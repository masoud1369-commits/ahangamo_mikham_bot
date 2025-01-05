import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# فعال‌سازی لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'  # توکن ربات تلگرام
YOUTUBE_API_KEY = 'AIzaSyBhwd2T6v4wSlEV69euIUfnUlrmknynS2g'  # کلید API YouTube
session = requests.Session()

# نگه‌داری نتایج جستجوی اخیر برای هر کاربر
user_search_results = {}

# دستور /start
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

# دستور /help
async def send_help(update: Update, context: CallbackContext):
    logger.info("Handling /help command")
    help_text = (
        "Commands:\n\n"
        "1. /start: Start the bot and see the welcome message.\n"
        "2. /help: Show usage instructions for the bot.\n"
        "3. /search [video name]: Search for videos on YouTube by their name.\n"
        "   - Example: /search funny cats\n"
        "4. Select a video and receive a modified download link."
    )

    await update.message.reply_text(help_text)

# دستور /search
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

# نمایش نتایج جستجو
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

# ارسال لینک دانلود اصلاح‌شده
async def send_modified_link(update: Update, context: CallbackContext):
    query = update.callback_query
    try:
        video_index = int(query.data.split("_")[1])
        selected_video = user_search_results[query.message.chat_id][video_index]
        logger.info(f"User selected video: {selected_video['title']}")

        # تغییر آدرس ویدیو
        original_url = selected_video['url']
        modified_url = original_url.replace("youtube.com", "youtubepp.com")

        logger.info("Modified YouTube URL for download: " + modified_url)

        # ارسال پیام زیبا به همراه لینک به کاربر
        response_text = (
            f"✅ ویدیو مورد نظر شما: <b>{selected_video['title']}</b>\n\n"
            f"⬇️ <b>روی لینک زیر بزنید</b> تا وارد صفحه دانلود شوید و بتوانید ویدیو مورد نظر را با کیفیت‌های مختلف دانلود کنید:\n\n"
            f"🔗 <a href='{modified_url}'>{modified_url}</a>"
        )

        await query.message.edit_text(response_text, parse_mode="HTML")
        await query.answer()
    except IndexError:
        logger.error("Invalid video selection.")
        await query.message.edit_text("❌ Invalid selection, please try again.")
        await query.answer()
    except Exception as e:
        logger.error(f"Error modifying the download link: {e}")
        await query.message.edit_text("❌ Failed to fetch the download link. Please try again later.")
        await query.answer()

# پیکربندی و اجرای ربات
def main():
    logger.info("Starting the bot application")
    application = Application.builder().token(TOKEN).build()

    # ثبت هندلرها
    application.add_handler(CommandHandler("start", send_welcome))
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(CommandHandler("search", search_video))
    application.add_handler(CallbackQueryHandler(send_modified_link, pattern=r"video_\d+"))

    # اجرای ربات
    application.run_polling()

if __name__ == "__main__":
    main()
