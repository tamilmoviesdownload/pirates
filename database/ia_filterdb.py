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
        if e.code == 85: 
            logger.warning("DATA_DATABASE_URL update index conflict. Recreating...")
            await updates_collection.drop_indexes() 
            await updates_collection.create_index([("title", ASCENDING), ("year", ASCENDING)], unique=True, name="title_year_unique")
        else:
            logger.exception(e)

    try:
        # Crucial for search speed with 2 million files
        await collection.create_index([("file_name", TEXT)], name="file_name_text")
        logger.info("FILES_DATABASE_URL indexes verified.")
    except OperationFailure as e:
        if e.code == 85: 
            await collection.drop_indexes() 
            await collection.create_index([("file_name", TEXT)], name="file_name_text")

    if SECOND_FILES_DATABASE_URL and second_collection is not None:
        try:
            await second_collection.create_index([("file_name", TEXT)], name="file_name_text")
        except:
            pass

async def second_db_count_documents():
    if second_collection is None: return 0
    return await second_collection.count_documents({})

async def db_count_documents():
    return await collection.count_documents({})

async def trigger_update_if_new(title, year):
    if not title: return
    normalized_title = str(title).strip().lower()
    try:
        await updates_collection.insert_one({"title": normalized_title, "year": year})
        asyncio.create_task(send_update(title, year))
    except DuplicateKeyError:
        pass

async def save_file(media, chat_id, message_id):
    base_file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    caption = str(media.caption) if media.caption else ""
    
    video_line, duration, audio, subtitle = "", "", "", ""

    if caption:
        clean_cap = re.sub(r'<[^>]+>', '', caption)
        
        vid_dur_match = re.search(r"🎬\s*(.*?)\s*\|\s*⏳\s*(.*)", clean_cap)
        if vid_dur_match:
            video_line = vid_dur_match.group(1).strip()
            duration = vid_dur_match.group(2).strip()

        audio_match = re.search(r"(?:🔊|Audio:)\s*(.*)", clean_cap, re.IGNORECASE)
        if audio_match:
            aud_text = audio_match.group(1).split('\n')[0].strip()
            aud_text = aud_text.replace("#", "") 
            if "💬" in aud_text: aud_text = aud_text.split("💬")[0]
            if "Subtitle" in aud_text: aud_text = aud_text.split("Subtitle")[0]
            audio = aud_text.strip()

        sub_match = re.search(r"(?:💬|Subtitle:)\s*(.*)", clean_cap, re.IGNORECASE)
        if sub_match:
            sub_text = sub_match.group(1).split('\n')[0].strip()
            subtitle = sub_text.replace("#", "").strip()

    searchable_name = f"{base_file_name} {audio}"
    searchable_name = re.sub(r"\s+", " ", searchable_name).strip()

    document = {
        '_id': f"{chat_id}_{message_id}",
        'file_name': searchable_name,
        'file_size': media.file_size,
        'chat_id': chat_id,
        'message_id': message_id,
        'video_line': video_line,
        'duration': duration,
        'audio': audio,
        'subtitle': subtitle
    }
    
    try:
        await collection.insert_one(document)
        logger.info(f'Saved - {searchable_name}')
        data = PTN.parse(base_file_name)
        await trigger_update_if_new(data.get('title'), data.get('year'))
        return 'suc'
    except DuplicateKeyError:
        return 'dup'
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return 'err'
        
async def get_search_results(query):
    query = str(query).strip()
    results = []

    # If query is empty, show recent 100 files
    if not query:
        cursor1 = collection.find({}).sort("_id", -1).limit(100)
        results = await cursor1.to_list(length=100)
        
        if SECOND_FILES_DATABASE_URL and second_collection is not None and len(results) < 100:
            cursor2 = second_collection.find({}).sort("_id", -1).limit(100 - len(results))
            docs2 = await cursor2.to_list(length=100 - len(results))
            results.extend(docs2)
        return results

    # Process search words for order-independent search
    words = query.split()
    and_filters = []
    for word in words:
        and_filters.append({"file_name": {"$regex": word, "$options": "i"}})
    
    search_filter = {"$and": and_filters}

    # Search Database 1
    cursor1 = collection.find(search_filter)
    docs1 = await cursor1.to_list(length=None) 
    results.extend(docs1)

    # Search Database 2
    if SECOND_FILES_DATABASE_URL and second_collection is not None:
        cursor2 = second_collection.find(search_filter)
        docs2 = await cursor2.to_list(length=None)
        results.extend(docs2)

    return results

async def delete_files(query):
    query = query.strip()
    if not query: return 0
    
    words = query.split()
    and_filters = [{"file_name": {"$regex": word, "$options": "i"}} for word in words]
    filter_query = {"$and": and_filters}
    
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
        if i == 0: n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    return encode_file_id(pack("<iiqq", int(decoded.file_type), decoded.dc_id, decoded.media_id, decoded.access_hash))
