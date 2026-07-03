import os
import random
import string
import asyncio
from time import time as time_now
from time import monotonic
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, WebAppInfo
from database.ia_filterdb import db_count_documents, second_db_count_documents, get_file_details, delete_files
from database.users_chats_db import db
from datetime import datetime, timedelta
from info import REQUESTS_CHANNEL, PREMIUM_PLANS, EFFECT_IDS, OWNER_USERNAME, IS_PREMIUM, URL, BIN_CHANNEL, SECOND_FILES_DATABASE_URL, INDEX_CHANNELS, ADMINS, IS_VERIFY, VERIFY_TUTORIAL, VERIFY_EXPIRE, SHORTLINK_API, SHORTLINK_URL, DELETE_TIME, SUPPORT_LINK, UPDATES_LINK, LOG_CHANNEL, PICS, IS_STREAM, REACTIONS, PM_FILE_DELETE_TIME
from utils import get_plan_name, get_poster, is_premium, upload_image, get_settings, get_size, is_subscribed, is_check_admin, get_shortlink, get_verify_status, update_verify_status, save_group_settings, temp, get_readable_time, get_wish, get_seconds
import PTN



@Client.on_message(filters.command("repair_mode") & filters.incoming)
async def repair_mode_cmd(client, message):
    if not message.from_user or message.from_user.id not in ADMINS:
        return await message.reply_text("You are not authorized to use this command.")
    
    args = message.text.split()
    if len(args) != 2 or args[1].lower() not in ["on", "off"]:
        return await message.reply_text("Usage: `/repair_mode on` or `/repair_mode off`")
    
    if args[1].lower() == "on":
        await db.set_repair_mode(True)
        await message.reply_text("Repair Mode activated successfully.")
    else:
        await db.set_repair_mode(False)
        await message.reply_text("Repair Mode deactivated successfully.")

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
        
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            username = f'@{message.chat.username}' if message.chat.username else 'Private'
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(message.chat.title, message.chat.id, username, total))       
            await db.add_chat(message.chat.id, message.chat.title)
        wish = get_wish()
        user = message.from_user.mention if message.from_user else "Dear"
        btn = [[
            InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️', url=UPDATES_LINK),
            InlineKeyboardButton('💡 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ 💡', url=SUPPORT_LINK)
        ]]
        await message.reply(text=f"<b>ʜᴇʏ {user}, <i>{wish}</i>\nʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>", reply_markup=InlineKeyboardMarkup(btn))
        return 
        
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        await message.react(emoji="⚡️", big=True)

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(message.from_user.mention, message.from_user.id))

    verify_status = await get_verify_status(message.from_user.id)
    if verify_status['is_verified'] and datetime.now() > verify_status['expire_time']:
        await update_verify_status(message.from_user.id, is_verified=False)


    if (len(message.command) != 2) or (len(message.command) == 2 and message.command[1] == 'start'):
        buttons = [[
            InlineKeyboardButton("+ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ +", url=f'http://t.me/{temp.U_NAME}?startgroup=start', style=enums.ButtonStyle.PRIMARY)
        ],[
            InlineKeyboardButton('ℹ️ ᴜᴘᴅᴀᴛᴇs', url=UPDATES_LINK),
            InlineKeyboardButton('🧑‍💻 sᴜᴘᴘᴏʀᴛ', url=SUPPORT_LINK)
        ],[
            InlineKeyboardButton('👨‍🚒 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('📚 ᴀʙᴏᴜᴛ', callback_data='about')
        ],[
            InlineKeyboardButton('🤑 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium"),
            InlineKeyboardButton('🔎 sᴇᴀʀᴄʜ ɪɴʟɪɴᴇ', switch_inline_query_current_chat=''),
        ],[
            InlineKeyboardButton('🎬 Popular Movie 🎬', url="https://www.themoviedb.org/movie"),
            InlineKeyboardButton('📺 Popular TV Shows 📺', url="https://www.themoviedb.org/tv")
        ],[
            InlineKeyboardButton('🌐 Mini WebApp 🌐', style=enums.ButtonStyle.SUCCESS, web_app=WebAppInfo(url=URL))
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, get_wish()),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
            effect_id=int(random.choice(EFFECT_IDS))
        )
        return

    mc = message.command[1]

    if mc == 'premium':
        return await plan(client, message)
    
    if mc.startswith('settings'):
        _, group_id = message.command[1].split("_")
        if not await is_check_admin(client, (int(group_id)), message.from_user.id):
            return await message.reply("You not admin in this group.")
        btn = await get_grp_stg(int(group_id))
        chat = await client.get_chat(int(group_id))
        return await message.reply(f"Change your settings for <b>'{chat.title}'</b> as your wish. ⚙", reply_markup=InlineKeyboardMarkup(btn))


    if mc.startswith('inline_fsub'):
        btn = await is_subscribed(client, message)
        if btn:
            reply_markup = InlineKeyboardMarkup(btn)
            await message.reply(f"Please join my 'Updates Channel' and use inline search. 👍",
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return 

    if mc.startswith('verify'):
        _, token = mc.split("_", 1)
        verify_status = (await get_verify_status(message.from_user.id)).copy()
        if verify_status['verify_token'] != token:
            return await message.reply("Your verify token is invalid.")
        expiry_time = datetime.now() + timedelta(seconds=VERIFY_EXPIRE)
        await update_verify_status(message.from_user.id, is_verified=True, expire_time=expiry_time)
        if verify_status["link"] == "":
            reply_markup = None
        else:
            btn = [[
                InlineKeyboardButton("📌 Get File 📌", url=f'https://t.me/{temp.U_NAME}?start={verify_status["link"]}')
            ]]
            reply_markup = InlineKeyboardMarkup(btn)
        await message.reply(f"✅ You successfully verified until: {get_readable_time(VERIFY_EXPIRE)}", reply_markup=reply_markup, protect_content=True)
        return
    
    verify_status = await get_verify_status(message.from_user.id)
    if IS_VERIFY and not verify_status['is_verified'] and not await is_premium(message.from_user.id, client):
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(message.from_user.id, verify_token=token, link="" if mc == 'inline_verify' else mc)
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{temp.U_NAME}?start=verify_{token}')
        btn = [[
            InlineKeyboardButton("🧿 Verify 🧿", url=link)
        ],[
            InlineKeyboardButton('🗳 Tutorial 🗳', url=VERIFY_TUTORIAL)
        ]]
        await message.reply("You not verified today! Kindly verify now. 🔐", reply_markup=InlineKeyboardMarkup(btn), protect_content=True)
        return

    btn = await is_subscribed(client, message)
    if btn:
        btn.append(
            [InlineKeyboardButton("🔁 Try Again 🔁", callback_data=f"checksub#{mc}")]
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=f"👋 Hello {message.from_user.mention},\n\nPlease join my 'Updates Channel' and try again. 😇",
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return 
        
# ... (previous code for start command)

    if mc.startswith('all'):
        _, grp_id, key = mc.split("_", 2)
        files = temp.GET_ALL_FILES.get(key)
        if not files:
            return await message.reply('No Such All Files Exist!')
        
        settings = await get_settings(int(grp_id))
        file_ids = []
        total_files_msg = await message.reply(f"<b><i>🗂 Total files - <code>{len(files)}</code></i></b>")
        
        for file in files:
            # Fetch scraped data for "Send All" items
            v_line = file.get('video_line', 'N/A')
            dur = file.get('duration', 'N/A')
            aud = file.get('audio', 'N/A')
            sub = file.get('subtitle', 'N/A')
            
            # Use the new custom template
            f_caption = (
                f"📌 <b>{file['file_name']}</b>\n\n"
                f"⚜️ Powered By : [ {message.chat.title if message.chat.title else 'ᴛᴀᴍɪʟ ᴍᴏᴠɪᴇꜱ'} ]\n"
                f"───────────────────\n"
                f"<blockquote>🎬 <code>{v_line}</code>  |  ⏳ <code>{dur}</code></blockquote>\n"
                f"<blockquote>🔊 <b>Audio:</b> {aud}</blockquote>\n"
                f"<blockquote>💬 <b>Subtitle:</b> {sub}</blockquote>"
            )

            if IS_STREAM:
                btn = [[
                    InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file['_id']}")
                ],[
                    InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
                ]]
            else:
                btn = [[
                    InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
                ]]

            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file['_id'],
                caption=f_caption,
                protect_content=settings.get('file_secure', False),
                reply_markup=InlineKeyboardMarkup(btn)
            )
            file_ids.append(msg.id)
            await asyncio.sleep(2)

        time_val = get_readable_time(PM_FILE_DELETE_TIME)
        vp = await message.reply(f"Nᴏᴛᴇ: Tʜɪs ғɪʟᴇs ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇ ɪɴ {time_val} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛs. Sᴀᴠᴇ ᴛʜᴇ ғɪʟᴇs ᴛᴏ sᴏᴍᴇᴡʜᴇʀᴇ ᴇʟsᴇ")
        await asyncio.sleep(PM_FILE_DELETE_TIME)
        buttons = [[InlineKeyboardButton('ɢᴇᴛ ғɪʟᴇs ᴀɢᴀɪɴ', callback_data=f"get_del_send_all_files#{grp_id}#{key}")]] 
        await client.delete_messages(chat_id=message.chat.id, message_ids=file_ids + [total_files_msg.id])
        await vp.edit("Tʜᴇ ғɪʟᴇ ʜᴀs ʙᴇᴇɴ ɢᴏɴᴇ ! Cʟɪᴄᴋ ɢɪᴠᴇɴ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪᴛ ᴀɢᴀɪɴ.", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # --- Handling Individual File Links ---
    parts = mc.split("_", 2)
    type_ = parts[0]
    grp_id = parts[1] if len(parts) == 3 else 0
    file_id = parts[-1]
    
    files_ = await get_file_details(file_id)
    if not files_:
        return await message.reply('No Such File Exist!')
    
    files = files_
    settings = await get_settings(int(grp_id))

    if type_ != 'shortlink' and settings['shortlink'] and not await is_premium(message.from_user.id, client):
        link = await get_shortlink(settings['url'], settings['api'], f"https://t.me/{temp.U_NAME}?start=shortlink_{grp_id}_{file_id}")
        btn = [[InlineKeyboardButton("♻️ Get File ♻️", url=link)],
               [InlineKeyboardButton(settings['tutorial_name'], url=settings['tutorial'])]]
        await message.reply(f"[{get_size(files['file_size'])}] {files['file_name']}\n\nYour file is ready, Please get using this link. 👍", reply_markup=InlineKeyboardMarkup(btn), protect_content=True)
        return
            
    # New Scraped Data
    v_line = files.get('video_line', 'N/A')
    dur = files.get('duration', 'N/A')
    aud = files.get('audio', 'N/A')
    sub = files.get('subtitle', 'N/A')
    f_name = files.get('file_name', 'Unknown')

    try:
        chat = await client.get_chat(int(grp_id))
        g_title = chat.title
    except:
        g_title = "ᴛᴀᴍɪʟ ᴍᴏᴠɪᴇꜱ"

    f_caption = (
        f"📌 <b>{f_name}</b>\n\n"
        f"⚜️ Powered By : [ {g_title} ]\n"
        f"───────────────────\n"
        f"<blockquote>🎬 <code>{v_line}</code>  |  ⏳ <code>{dur}</code></blockquote>\n"
        f"<blockquote>🔊 <b>Audio:</b> {aud}</blockquote>\n"
        f"<blockquote>💬 <b>Subtitle:</b> {sub}</blockquote>"
    )

    if IS_STREAM:
        btn = [[InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file_id}")],
               [InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')]]
    else:
        btn = [[InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')]]

    vp = await client.copy_message(
        chat_id=message.from_user.id,
        from_chat_id=files['chat_id'],   
        message_id=files['message_id'], 
        caption=f_caption,
        reply_markup=InlineKeyboardMarkup(btn)
    )
    
    time_val = get_readable_time(PM_FILE_DELETE_TIME)
    msg = await vp.reply(f"Nᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇ ɪɴ {time_val} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛs. Sᴀᴠᴇ ᴛʜᴇ ғɪʟᴇ ᴛᴏ sᴏᴍᴇᴡʜᴇʀᴇ ᴇʟsᴇ")
    await asyncio.sleep(PM_FILE_DELETE_TIME)
    btns = [[InlineKeyboardButton('ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ', callback_data=f"get_del_file#{grp_id}#{file_id}")]]
    await msg.delete()
    await vp.delete()
    await vp.reply("Tʜᴇ ғɪʟᴇ ʜᴀs ʙᴇᴇɴ ɢᴏɴᴇ ! Cʟɪᴄᴋ ɢɪᴠᴇɴ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪᴛ ᴀɢᴀɪɴ.", reply_markup=InlineKeyboardMarkup(btns))

@Client.on_message(filters.command('link'))
async def link(bot, message):
    msg = message.reply_to_message
    if not msg:
        return await message.reply('Reply to a media file.')
        
    m=await message.reply('Processing.....')
    try:
        media = getattr(msg, msg.media.value)
        vidking_url = None
        if media.file_name:
            parsed = PTN.parse(media.file_name)
            title = parsed.get('title')
            year = parsed.get('year')
            season = parsed.get('season')
            episode = parsed.get('episode')
            if title:
                query = str(title)
                if year:
                    query += f" {year}"
                poster_data = await get_poster(query)
                if poster_data:
                    tmdb_id = poster_data['tmdb_id']
                    if season is not None:
                        if episode is not None:
                            vidking_url = f"https://www.vidking.net/embed/tv/{tmdb_id}/{season}/{episode}?episodeSelector=true"
                        else:
                            vidking_url = f"https://www.vidking.net/embed/tv/{tmdb_id}/{season}/1?episodeSelector=true"
                    else:
                        vidking_url = f"https://www.vidking.net/embed/movie/{tmdb_id}"

        bin_msg = await bot.send_cached_media(chat_id=BIN_CHANNEL, file_id=media.file_id)
        watch = f"{URL}watch/{bin_msg.id}"
        download = f"{URL}download/{bin_msg.id}"
        btn = []
        if vidking_url:
            btn.append([
                InlineKeyboardButton("🌐 Smart Player 🌐", url=vidking_url)
            ])
        btn.append([
            InlineKeyboardButton("ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=watch),
            InlineKeyboardButton("ꜰᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ", url=download)
        ])
        btn.append([
            InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
        ])
        await m.edit('Here are your links:', reply_markup=InlineKeyboardMarkup(btn))
    except Exception as e:
        await m.edit(f'An error occurred: {e}')


@Client.on_message(filters.command('index_channels'))
async def channels_info(bot, message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    ids = INDEX_CHANNELS
    if not ids:
        return await message.reply("Not set INDEX_CHANNELS")
    text = '**Indexed Channels:**\n\n'
    for id in ids:
        chat = await bot.get_chat(id)
        text += f'{chat.title}\n'
    text += f'\n**Total:** {len(ids)}'
    await message.reply(text)

@Client.on_message(filters.command('stats'))
async def stats(bot, message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    files = await db_count_documents()
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    prm = await db.get_premium_count()
    used_files_db_size = get_size(await db.get_files_db_size())
    used_data_db_size = get_size(await db.get_data_db_size())

    if SECOND_FILES_DATABASE_URL:
        secnd_files_db_used_size = get_size(await db.get_second_files_db_size())
        secnd_files = await second_db_count_documents()
    else:
        secnd_files_db_used_size = '-'
        secnd_files = '-'

    uptime = get_readable_time(time_now() - temp.START_TIME)
    await message.reply_text(script.STATUS_TXT.format(users, prm, chats, used_data_db_size, files, used_files_db_size, secnd_files, secnd_files_db_used_size, uptime))    
    


async def get_grp_stg(group_id):
    btn = [[
        InlineKeyboardButton('Shortlink Settings', callback_data=f'shortlink_menu#{group_id}'),
        InlineKeyboardButton('IMDb Settings', callback_data=f'imdb_menu#{group_id}')
    ],[
        InlineKeyboardButton('Welcome Settings', callback_data=f'welcome_menu#{group_id}'),
        InlineKeyboardButton('Caption Settings', callback_data=f'caption_menu#{group_id}')
    ],[
        InlineKeyboardButton('Auto Delete Settings', callback_data=f'auto_delete_menu#{group_id}'),
        InlineKeyboardButton('Tutorial Settings', callback_data=f'tutorial_setgs#{group_id}')
    ],[
        InlineKeyboardButton('Miscellaneous Settings', callback_data=f'misc_menu#{group_id}')
    ],[
        InlineKeyboardButton('Close', callback_data='close_data')
    ]]
    return btn
    
@Client.on_message(filters.command('settings'))
async def settings(client, message):
    group_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await is_check_admin(client, group_id, message.from_user.id):
            return await message.reply_text('You not admin in this group.')
        btn = [[
            InlineKeyboardButton("Open Here", callback_data='open_group_settings')
        ],[
            InlineKeyboardButton("Open In PM", callback_data='open_pm_settings')
        ]]
        await message.reply_text('Where do you want to open the settings menu?', reply_markup=InlineKeyboardMarkup(btn))
    elif message.chat.type == enums.ChatType.PRIVATE:
        cons = await db.get_connections(message.from_user.id)
        if not cons:
            return await message.reply_text("No groups found! Use this command group and open in PM")
        buttons = []
        for con in cons:
            try:
                chat = await client.get_chat(con)
                buttons.append(
                    [InlineKeyboardButton(text=chat.title, callback_data=f'back_setgs#{chat.id}')]
                )
            except:
                pass
        await message.reply_text('Select the group whose settings you want to change.\n\nIf your group not showing here? Use this command in your group and open in PM or send <code>/connect</code> command in your group.', reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_message(filters.command('connect'))
async def connect(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group_id = message.chat.id
        await db.add_connect(group_id, message.from_user.id)
        await message.reply_text('Successfully connected this group to PM, now you can manage your group using /settings inside your PM')
    elif message.chat.type == enums.ChatType.PRIVATE:
        if len(message.command) > 1:
            group_id = message.command[1]
            if not await is_check_admin(client, int(group_id), message.from_user.id):
                return await message.reply_text('You not admin in this group.')
            chat = await client.get_chat(int(group_id))
            await db.add_connect(int(group_id), message.from_user.id)
            await message.reply_text(f'Successfully connected {chat.title} group to PM')
        else:
            await message.reply_text('Usage: /connect group_id\nor use /connect in group')


@Client.on_message(filters.command('delete'))
async def delete_file(bot, message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    try:
        query = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!\nUsage: /delete query")
    btn = [[
        InlineKeyboardButton("YES", callback_data=f"delete_{query}")
    ],[
        InlineKeyboardButton("CLOSE", callback_data="close_data")
    ]]
    await message.reply_text(f"Do you want to delete all: {query} ?", reply_markup=InlineKeyboardMarkup(btn))
 


@Client.on_message(filters.command('img_2_link'))
async def img_2_link(bot, message):
    reply_to_message = message.reply_to_message
    if not reply_to_message:
        return await message.reply('Reply to any photo')
    file = reply_to_message.photo
    if file is None:
        return await message.reply('Invalid media.')
    text = await message.reply_text(text="ᴘʀᴏᴄᴇssɪɴɢ....")   
    path = await reply_to_message.download()  
    response = upload_image(path)
    if not response:
         await text.edit_text(text="Upload failed!")
         return    
    try:
        os.remove(path)
    except:
        pass
    await text.edit_text(f"<b>❤️ Your link ready 👇\n\n{response}</b>", link_preview_options=LinkPreviewOptions(is_disabled=True))

@Client.on_message(filters.command('ping'))
async def ping(client, message):
    start_time = monotonic()
    msg = await message.reply("👀")
    end_time = monotonic()
    await msg.edit(f'{round((end_time - start_time) * 1000)} ms')
    

@Client.on_message(filters.command('myplan') & filters.private)
async def myplan(client, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled by admin')
    mp = await db.get_plan(message.from_user.id)
    if not await is_premium(message.from_user.id, client):
        btn = [[
            InlineKeyboardButton('Activate Trial', callback_data='activate_trial'),
            InlineKeyboardButton('Activate Plan', callback_data='activate_plan')
        ]]
        return await message.reply('You dont have any premium plan, please use /plan to activate plan', reply_markup=InlineKeyboardMarkup(btn))
    ex = mp.get('expire').strftime('%Y.%m.%d %H:%M:%S') if mp.get('expire') else 'Unknow'
    await message.reply(f"You activated {mp.get('plan') or 'Unknow plan'}\nExpire: {ex}")


@Client.on_message(filters.command('plan') & filters.private)
async def plan(client, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled by admin')
    btn = [[
        InlineKeyboardButton('Activate Trial', callback_data='activate_trial')
    ],[
        InlineKeyboardButton('Activate Plan', callback_data='activate_plan')
    ]]
    plans_list = []
    for days, details in PREMIUM_PLANS.items():
        name = get_plan_name(days)
        currency = details[0]
        price = details[1]
        plans_list.append(f"▫️ {name} — {currency} {price}")
    PLANS_BLOCK = "\n".join(plans_list)
    await message.reply(script.PLAN_TXT.format(PLANS_BLOCK, OWNER_USERNAME), reply_markup=InlineKeyboardMarkup(btn))


@Client.on_message(filters.command('add_prm') & filters.user(ADMINS))
async def add_prm(bot, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    try:
        _, user_id, d = message.text.split(' ')
    except:
        return await message.reply('Usage: /add_prm user_id 1d')
    try:
        d = int(d[:-1])
    except:
        return await message.reply('Not valid days, use: 1d, 7d, 30d, 365d, etc...')
    try:
        user = await bot.get_users(int(user_id))
    except Exception as e:
        return await message.reply(f'Error: {e}')
    if user.id in ADMINS:
        return await message.reply('ADMINS is already premium')
    if not await is_premium(user.id, bot):
        mp = await db.get_plan(user.id)
        ex = datetime.now() + timedelta(days=d)
        mp['expire'] = ex
        mp['plan'] = get_plan_name(d)
        mp['premium'] = True
        await db.update_plan(user.id, mp)
        await message.reply(f"Given premium to {user.mention}\nExpire: {ex.strftime('%Y.%m.%d %H:%M:%S')}")
        try:
            await bot.send_message(user.id, f"Your now premium user\nExpire: {ex.strftime('%Y.%m.%d %H:%M:%S')}")
        except:
            pass
    else:
        await message.reply(f"{user.mention} is already premium user")



@Client.on_message(filters.command('rm_prm') & filters.user(ADMINS))
async def rm_prm(bot, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    try:
        _, user_id = message.text.split(' ')
    except:
        return await message.reply('Usage: /rm_prm user_id')
    try:
        user = await bot.get_users(int(user_id))
    except Exception as e:
        return await message.reply(f'Error: {e}')
    if user.id in ADMINS:
        return await message.reply('ADMINS is already premium')
    if not await is_premium(user.id, bot):
        await message.reply(f"{user.mention} is not premium user")
    else:
        mp = await db.get_plan(user.id)
        mp['expire'] = ''
        mp['plan'] = ''
        mp['premium'] = False
        await db.update_plan(user.id, mp)
        await message.reply(f"{user.mention} is no longer premium user")
        try:
            await bot.send_message(user.id, "Your premium plan was removed by admin")
        except:
            pass


@Client.on_message(filters.command('prm_list') & filters.user(ADMINS))
async def prm_list(bot, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    tx = await message.reply('Getting list of premium users')
    pr = [i['id'] for i in await db.get_premium_users() if i['status']['premium']]
    t = 'premium users saved in database are:\n\n'
    for p in pr:
        try:
            u = await bot.get_users(p)
            t += f"{u.mention} : {p}\n"
        except:
            t += f"{p}\n"
    await tx.edit_text(t)





@Client.on_message(filters.command('request'))
async def request_cmd(bot, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Please provide a movie/tv show name.\n\nExample: `/request Interstellar`")
        
    movie_name = message.text.split(" ", 1)[1]
    req_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    await db.add_movie_req(req_id, message.from_user.id, movie_name)
    
    btn = [[
        InlineKeyboardButton("✅ Completed", callback_data=f"req_completed#{req_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"req_reject#{req_id}")
    ]]
    
    try:
        await bot.send_message(
            REQUESTS_CHANNEL, 
            f"#Request\n\n★ User: {message.from_user.mention}\n★ User ID: `{message.from_user.id}`\n\n★ Message: {movie_name}",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        await message.reply("✅ Your request has been sent successfully!")
    except Exception as e:
        await message.reply(f"Failed to send request. Error: {e}")

