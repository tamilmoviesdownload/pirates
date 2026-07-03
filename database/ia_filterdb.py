import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import TEXT, ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
from info import USE_CAPTION_FILTER, FILES_DATABASE_URL, SECOND_FILES_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN, DATA_DATABASE_URL
import PTN, asyncio
from database.users_chats_db import data_db
from utils import send_update

logger = logging.getLogger(__name__)

client = AsyncIOMotorClient(FILES_DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

second_client = None
second_db = None
second_collection = None

if SECOND_FILES_DATABASE_URL:
    second_client = AsyncIOMotorClient(SECOND_FILES_DATABASE_URL)
    second_db = second_client[DATABASE_NAME]
    second_collection = second_db[COLLECTION_NAME]

updates_collection = data_db['notified_media']

async def setup_database():
    try:
        await updates_collection.create_index(
            [("title", ASCENDING), ("year", ASCENDING)],
            unique=True,
            name="title_year_unique"
        )
        logger.info("DATA_DATABASE_URL update indexes created/verified.")
    except OperationFailure as e:
        if e.code == 85:  # IndexOptionsConflict
            logger.warning("DATA_DATABASE_URL update index conflict detected. Dropping old indexes and recreating...")
            await updates_collection.drop_indexes() 
            await updates_collection.create_index(
                [("title", ASCENDING), ("year", ASCENDING)],
                unique=True,
                name="title_year_unique"
            )
            logger.info("DATA_DATABASE_URL update indexes recreated successfully.")
        else:
            logger.exception(e)
            exit()

    try:
        await collection.create_index([("file_name", TEXT), ("caption", TEXT)], name="file_name_caption_text")
        logger.info("FILES_DATABASE_URL indexes created/verified.")
    except OperationFailure as e:
        if e.code == 85:  # IndexOptionsConflict
            logger.warning("FILES_DATABASE_URL index conflict detected. Dropping old text indexes and recreating...")
            await collection.drop_indexes() 
            await collection.create_index([("file_name", TEXT), ("caption", TEXT)], name="file_name_caption_text")
            logger.info("FILES_DATABASE_URL indexes recreated successfully.")
        elif 'quota' in str(e).lower():
            if not SECOND_FILES_DATABASE_URL:
                logger.error('Your FILES_DATABASE_URL quota is full, add SECOND_FILES_DATABASE_URL. (Bot will still work for searching)')
            else:
                logger.info('FILES_DATABASE_URL quota is full, relying on SECOND_FILES_DATABASE_URL')
        else:
            logger.exception(e)
            exit() 

    if SECOND_FILES_DATABASE_URL and second_collection is not None:
        try:
            await second_collection.create_index([("file_name", TEXT), ("caption", TEXT)], name="file_name_caption_text")
            logger.info("SECOND_FILES_DATABASE_URL indexes created/verified.")
        except OperationFailure as e:
            if e.code == 85:
                logger.warning("SECOND_FILES_DATABASE_URL index conflict detected. Dropping old text indexes and recreating...")
                await second_collection.drop_indexes()
                await second_collection.create_index([("file_name", TEXT), ("caption", TEXT)], name="file_name_caption_text")
                logger.info("SECOND_FILES_DATABASE_URL indexes recreated successfully.")
            else:
                logger.exception(e)
                exit()


async def second_db_count_documents():
    if second_collection is None:
        return 0
    return await second_collection.count_documents({})

async def db_count_documents():
    return await collection.count_documents({})


async def trigger_update_if_new(title, year):
    if not title:
        return
    normalized_title = str(title).strip().lower()
    try:
        await updates_collection.insert_one({
            "title": normalized_title, 
            "year": year
        })
        asyncio.create_task(send_update(title, year))
    except DuplicateKeyError:
        pass


# database/ia_filterdb.py

async def save_file(media, chat_id, message_id):
    # Basic cleaning for the searchable filename
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    caption = str(media.caption) if media.caption else ""
    
    # Initialize fields
    video_line = "N/A"
    duration = "N/A"
    audio = "N/A"
    subtitle = "N/A"

    if caption:
        # Strip HTML for regex cleaning
        clean_cap = re.sub(r'<[^>]+>', '', caption)
        
        # 1. Extract Video Line and Duration
        # Matches: 🎬 1080p HEVC 10bit | ⏳ 01:48:53
        vid_dur_match = re.search(r"🎬\s*(.*?)\s*\|\s*⏳\s*(.*)", clean_cap)
        if vid_dur_match:
            video_line = vid_dur_match.group(1).strip()
            duration = vid_dur_match.group(2).strip()

        # 2. Extract Audio
        audio_match = re.search(r"Audio:\s*(.*)", clean_cap, re.IGNORECASE)
        if audio_match:
            audio = audio_match.group(1).split('\n')[0].strip()
            if "Subtitle" in audio: audio = audio.split("Subtitle")[0].strip()
            audio = re.sub(r"[🔊💬📌🎬⏳|]", "", audio).strip()

        # 3. Extract Subtitle
        sub_match = re.search(r"Subtitle:\s*(.*)", clean_cap, re.IGNORECASE)
        if sub_match:
            subtitle = sub_match.group(1).split('\n')[0].strip()
            subtitle = re.sub(r"[🔊💬📌🎬⏳|]", "", subtitle).strip()

    # Append audio to filename for search results
    if audio != "N/A":
        file_name = f"{file_name} {audio}"

    document = {
        '_id': f"{chat_id}_{message_id}",
        'file_name': file_name,
        'file_size': media.file_size,
        'chat_id': chat_id,
        'message_id': message_id,
        # Store separate fields for the new template
        'video_line': video_line,
        'duration': duration,
        'audio': audio,
        'subtitle': subtitle
    }
    
    try:
        await collection.insert_one(document)
        logger.info(f'Saved - {file_name}')
        # PTN for the updates channel
        data = PTN.parse(file_name)
        await trigger_update_if_new(data.get('title'), data.get('year'))
        return 'suc'
    except DuplicateKeyError:
        return 'dup'
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return 'err'
        
async def get_search_results(query):
    query = str(query).strip()
    if not query:
        recent_limit = 100  # default limit for fetching recently added files
        results = []
        
        cursor1 = collection.find({}).sort("_id", -1).limit(recent_limit)
        docs1 = await cursor1.to_list(length=recent_limit)
        results.extend(docs1)

        if SECOND_FILES_DATABASE_URL and second_collection is not None and len(results) < recent_limit:
            remaining_limit = recent_limit - len(results)
            cursor2 = second_collection.find({}).sort("_id", -1).limit(remaining_limit)
            docs2 = await cursor2.to_list(length=remaining_limit)
            results.extend(docs2)

        return results

    if ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')

    db_query = {"$regex": raw_pattern, "$options": "i"}
    search_filter = {"$or": [{"file_name": db_query}]}
    
    if USE_CAPTION_FILTER:
        search_filter["$or"].append({"caption": db_query})

    results = []
    
    cursor1 = collection.find(search_filter)
    docs1 = await cursor1.to_list(length=None) 
    results.extend(docs1)

    if SECOND_FILES_DATABASE_URL and second_collection is not None:
        cursor2 = second_collection.find(search_filter)
        docs2 = await cursor2.to_list(length=None)
        results.extend(docs2)

    return results


async def delete_files(query):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
        
    filter_query = {'file_name': regex}
    
    result1 = await collection.delete_many(filter_query)
    total_deleted = result1.deleted_count
    
    if SECOND_FILES_DATABASE_URL and second_collection is not None:
        result2 = await second_collection.delete_many(filter_query)
        total_deleted += result2.deleted_count
    
    return total_deleted


async def get_file_details(query):
    file_details = await collection.find_one({'_id': query})
    if not file_details and SECOND_FILES_DATABASE_URL and second_collection is not None:
        file_details = await second_collection.find_one({'_id': query})
    return file_details


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id

