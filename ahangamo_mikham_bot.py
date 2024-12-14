import logging
import yt_dlp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# فعال‌سازی لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'  # توکن ربات تلگرام
YOUTUBE_API_KEY = 'AIzaSyBhwd2T6v4wSlEV69euIUfnUlrmknynS2g'  # کلید API YouTube
COOKIES_PATH = 'cookies.txt'  # مسیر فایل کوکی
session = requests.Session()

# نگه‌داری نتایج جستجوی اخیر برای هر کاربر
user_search_results = {}

# دستوراتی که کاربر می‌تواند استفاده کند:
# /start: نمایش پیام خوشامدگویی
# /help: نمایش دستورالعمل‌ها و راهنمای استفاده از ربات
# /search [video name]: جستجوی ویدیو در یوتیوب و نمایش نتایج

# تابع ارسال پیام خوشامدگویی
async def send_welcome(update: Update, context: CallbackContext):
    logger.info("Handling /start command")
    keyboard = [
        [InlineKeyboardButton("Start", callback_data='start')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Welcome! Use this bot to search and download YouTube videos. Press 'Start' to begin.",
        reply_markup=reply_markup
    )

# تابع ارسال راهنمایی
async def send_help(update: Update, context: CallbackContext):
    logger.info("Handling /help command")
    help_text = (
        "Commands:\n\n"
        "1. /start: Start the bot and see the welcome message.\n"
        "2. /help: Show usage instructions for the bot.\n"
        "3. /search [video name]: Search for videos on YouTube by their name.\n"
        "   - Example: /search funny cats\n"
        "4. Follow the on-screen instructions to select video format and download."
    )

    await update.message.reply_text(help_text)

# تابع جستجو ویدیو
async def search_video(update: Update, context: CallbackContext):
    logger.info("Handling /search command")
    video_name = ' '.join(context.args) if context.args else None
    if not video_name:
        logger.warning("No video name provided in /search command")
        await update.message.reply_text("Please provide a video name to search.")
        return

    try:
        logger.info(f"Searching for video: {video_name}")
        response = session.get("https://www.googleapis.com/youtube/v3/search", params={
            'part': 'snippet',
            'q': video_name,
            'key': YOUTUBE_API_KEY,
            'maxResults': 5
        })

        if response.status_code != 200:
            logger.error(f"YouTube API request failed with status code {response.status_code}")
            await update.message.reply_text(f"Error retrieving data from YouTube API. Status: {response.status_code}")
            return

        # تجزیه JSON
        data = response.json()
        video_results = []

        if 'items' in data and data['items']:
            logger.info("Parsing search results from YouTube API response")
            for item in data['items']:
                video_title = item['snippet']['title']
                video_id = item['id'].get('videoId', None)

                if video_id:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    video_results.append({
                        'title': video_title,
                        'url': video_url,
                        'id': video_id
                    })

            if video_results:
                logger.info("Search results found and stored")
                user_search_results[update.message.chat_id] = video_results
                await display_search_results(update, context, video_results)
            else:
                logger.warning("No suitable videos found in search results")
                await update.message.reply_text("No suitable videos found.")
        else:
            logger.warning("No videos found in search response")
            await update.message.reply_text("No videos found.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to YouTube API failed: {e}")
        await update.message.reply_text("Error connecting to YouTube API.")

# تابع نمایش نتایج جستجو
async def display_search_results(update: Update, context: CallbackContext, video_results):
    logger.info("Displaying search results to user")
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {video['title']}", callback_data=f"video_{i}")] for i, video in enumerate(video_results)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Please select a video:",
        reply_markup=reply_markup
    )

# تابع انتخاب نوع فایل (ویدیو یا صوتی)
async def choose_file_type(update: Update, context: CallbackContext):
    query = update.callback_query
    video_index = int(query.data.split("_")[1])
    selected_video = user_search_results[query.message.chat_id][video_index]

    logger.info(f"User selected video: {selected_video['title']}")

    keyboard = [
        [InlineKeyboardButton("🎥 Video", callback_data=f"filetype_video_{video_index}"),
         InlineKeyboardButton("🎵 Audio", callback_data=f"filetype_audio_{video_index}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"You selected:\n\n🎥 {selected_video['title']}\n\nChoose file type:",
                                  reply_markup=reply_markup)
    await query.answer()

# تابع انتخاب فرمت فایل
async def select_format(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    video_index = int(data.split("_")[2])
    selected_video = user_search_results[query.message.chat_id][video_index]

    logger.info(f"User is selecting format for video: {selected_video['title']}")

    # استفاده از yt-dlp برای استخراج فرمت‌های قابل دانلود
    ydl_opts = {
        'format': 'bestaudio/bestvideo',  # انتخاب بهترین کیفیت
        'noplaylist': True,  # فقط ویدیو یکسان را بگیرد، نه لیست پخش
        'quiet': True  # خاموش کردن نمایش اطلاعات اضافی
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(selected_video['url'], download=False)  # فقط اطلاعات را استخراج می‌کند
        formats = result.get('formats', [])

    # ساخت دکمه‌های فرمت
    if not formats:
        logger.warning("No downloadable formats available for the selected video")
        await query.message.edit_text("❌ No downloadable formats available for this video.")
        await query.answer()
        return

    keyboard = [
        [InlineKeyboardButton(f'{f["ext"]} {f["height"] if "height" in f else ""}', callback_data=f"download_{f['format_id']}_{video_index}") for f in formats]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"Selected video: {selected_video['title']}\n\nChoose format:",
                                  reply_markup=reply_markup)
    await query.answer()

# تابع ارسال لینک دانلود
async def send_download_link(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    parts = data.split("_")
    format_id = parts[1]
    video_index = int(parts[2])

    selected_video = user_search_results[query.message.chat_id][video_index]

    logger.info(f"Preparing download link for video: {selected_video['title']} with format ID: {format_id}")

# استفاده از yt-dlp برای دریافت لینک دانلود
    ydl_opts = {
        'format': format_id,
        'outtmpl': '%(id)s.%(ext)s',  # مسیر ذخیره فایل (در اینجا فقط لینک دانلود داده می‌شود)
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(selected_video['url'], download=False)
            download_link = result.get('url', None)

        if download_link:
            logger.info("Download link generated successfully")
            download_link = shorten_url(download_link)
            await query.message.edit_text(
                f"✅ Your file is ready!\n\n🎥 Video: {selected_video['title']}\n🔗 Download link: {download_link}")
        else:
            logger.error("Download link could not be generated")
            await query.message.edit_text("❌ Unable to generate a download link for this video.")
    except Exception as e:
        logger.error(f"Error generating download link: {e}")
        await query.message.edit_text("❌ Error generating the download link. Please try again later.")

    await query.answer()

# تابع تبدیل لینک به کوتاه
def shorten_url(url):
    try:
        logger.info("Shortening URL")
        response = requests.get(f'https://api.shrtco.de/v2/shorten?url={url}')
        if response.status_code == 201:
            short_url = response.json()['result']['short_link']
            logger.info(f"URL shortened successfully: {short_url}")
            return short_url
        logger.warning(f"Failed to shorten URL, using original: {url}")
        return url
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
        return url

# اصلی‌ترین تابع
def main():
    logger.info("Starting the bot...")
    application = Application.builder().token(TOKEN).build()

    # دستورات و دکمه‌ها
    application.add_handler(CommandHandler("start", send_welcome))
    application.add_handler(CommandHandler("search", search_video))
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(CallbackQueryHandler(choose_file_type, pattern='^video_\\d+$'))
    application.add_handler(CallbackQueryHandler(select_format, pattern='^filetype_(video|audio)_\\d+$'))
    application.add_handler(CallbackQueryHandler(send_download_link, pattern='^download_\\w+_\\d+$'))

    logger.info("Bot is now running. Waiting for user commands...")
    application.run_polling()

if __name__ == '__main__':
    main()
