import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import requests

# فعال‌سازی لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'  # توکن ربات تلگرام خود را وارد کنید
YOUTUBE_API_KEY = 'AIzaSyBhwd2T6v4wSlEV69euIUfnUlrmknynS2g'  # کلید API YouTube خود را وارد کنید
session = requests.Session()

# تابع ارسال دکمه‌ها
async def send_welcome(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("جستجوی ویدیو", callback_data='search')],
        [InlineKeyboardButton("درباره ربات", callback_data='about')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "سلام! خوش آمدید به ربات جستجوی ویدیو. برای شروع یکی از گزینه‌ها را انتخاب کنید.",
        reply_markup=reply_markup
    )

# تابع نمایش پیام توضیحی در مورد ربات
async def explain_usage(update: Update, context: CallbackContext):
    message = """
    خوش آمدید به ربات جستجوی ویدیو! 

    برای جستجوی یک ویدیو:
    1. از دستور "/search <نام ویدیو>" استفاده کنید.
    2. نام ویدیو را به صورت دقیق وارد کنید تا ربات بتواند آن را پیدا کند.
    3. پس از وارد کردن نام ویدیو، ربات لینک ویدیو را از YouTube برای شما ارسال خواهد کرد.

    برای مثال:
    /search Bohemian Rhapsody
    """
    await update.callback_query.message.edit_text(message)
    await update.callback_query.answer()

# تابع جستجو ویدیو
async def search_video(update: Update, context: CallbackContext):
    video_name = ' '.join(context.args) if context.args else None
    if not video_name:
        await update.message.reply_text("لطفاً نام ویدیو را وارد کنید.")
        return
    
    try:
        # درخواست جستجو به YouTube API
        response = session.get("https://www.googleapis.com/youtube/v3/search", params={
            'part': 'snippet',
            'q': video_name,
            'key': YOUTUBE_API_KEY,
            'maxResults': 1
        })

        # بررسی وضعیت پاسخ
        if response.status_code != 200:
            await update.message.reply_text(f"خطا در دریافت اطلاعات از API. وضعیت: {response.status_code}")
            logger.error(f"Request failed with status code {response.status_code}")
            return

        # تجزیه JSON
        data = response.json()

        if 'items' in data and data['items']:
            video = data['items'][0]
            video_title = video['snippet']['title']
            video_description = video['snippet']['description']
            video_url = f"https://www.youtube.com/watch?v={video['id']['videoId']}"

            await update.message.reply_text(
                f"🎥 **{video_title}**\n\n"
                f"📃 توضیحات: {video_description[:150]}...\n\n"
                f"🔗 لینک ویدیو: {video_url}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("ویدیو پیدا نشد.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text("خطا در ارتباط با API.")
        logger.error(f"Request failed: {e}")

# تابع شروع
async def start(update: Update, context: CallbackContext):
    await send_welcome(update, context)

# تابع ارسال اطلاعات درباره ربات
async def about_robot(update: Update, context: CallbackContext):
    message = """
    این ربات برای جستجوی ویدیوها از YouTube استفاده می‌کند.
    
    امکانات:
    - جستجوی ویدیوها بر اساس نام
    - ارسال لینک ویدیو به همراه توضیحات
    
    برای شروع، از دکمه‌ها یا دستورات استفاده کنید.
    """
    await update.callback_query.message.edit_text(message)
    await update.callback_query.answer()

# اصلی‌ترین تابع
def main():
    try:
        application = Application.builder().token(TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("search", search_video))  # جستجو در YouTube
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_video))  # جستجو در YouTube

        # دکمه‌های مربوط به ربات
        application.add_handler(CallbackQueryHandler(explain_usage, pattern='^search$'))
        application.add_handler(CallbackQueryHandler(about_robot, pattern='^about$'))

        logger.info("ربات در حال اجراست...")
        application.run_polling()
    except Exception as e:
        logger.error(f"خطای غیرمنتظره: {e}")

if __name__ == '__main__':
    main()
