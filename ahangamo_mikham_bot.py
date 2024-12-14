import logging
import yt_dlp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters

# فعال‌سازی لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'  # توکن ربات تلگرام
YOUTUBE_API_KEY = 'AIzaSyBhwd2T6v4wSlEV69euIUfnUlrmknynS2g'  # کلید API YouTube
session = requests.Session()

# نگه‌داری نتایج جستجوی اخیر برای هر کاربر
user_search_results = {}

# تابع ارسال پیام خوشامدگویی
async def send_welcome(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("شروع", callback_data='start')],
        [InlineKeyboardButton("راهنما", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "سلام! خوش آمدید به ربات جستجوی ویدیو. برای شروع دکمه 'شروع' را فشار دهید.",
        reply_markup=reply_markup
    )

# تابع ارسال راهنمایی
async def send_help(update: Update, context: CallbackContext):
    help_text = (
        "دستورات ربات:\n\n"
        "1. دکمه 'شروع' را فشار دهید تا شروع به جستجوی ویدیو کنید.\n"
        "2. نام ویدیو را وارد کنید تا نتایج جستجو برای شما نمایش داده شود.\n"
        "3. پس از انتخاب ویدیو، نوع فایل (ویدیو یا صوتی) را انتخاب کنید.\n"
        "4. فرمت دلخواه خود (مانند mp4 360p یا MP3) را انتخاب کنید.\n"
        "5. لینک دانلود برای شما ارسال می‌شود."
    )

    await update.message.reply_text(help_text)

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
            'maxResults': 5
        })

        if response.status_code != 200:
            await update.message.reply_text(f"خطا در دریافت اطلاعات از API. وضعیت: {response.status_code}")
            logger.error(f"Request failed with status code {response.status_code}")
            return

        # تجزیه JSON
        data = response.json()
        video_results = []

        if 'items' in data and data['items']:
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
                user_search_results[update.message.chat_id] = video_results
                await display_search_results(update, context, video_results)
            else:
                await update.message.reply_text("ویدیو مناسب پیدا نشد.")
        else:
            await update.message.reply_text("ویدیو پیدا نشد.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text("خطا در ارتباط با API.")
        logger.error(f"Request failed: {e}")

# تابع نمایش نتایج جستجو
async def display_search_results(update: Update, context: CallbackContext, video_results):
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {video['title']}", callback_data=f"video_{i}") for i, video in enumerate(video_results)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "لطفاً یکی از ویدیوها را انتخاب کنید:",
        reply_markup=reply_markup
    )

# تابع انتخاب نوع فایل (ویدیو یا صوتی)
async def choose_file_type(update: Update, context: CallbackContext):
    query = update.callback_query
    video_index = int(query.data.split("_")[1])
    selected_video = user_search_results[query.message.chat_id][video_index]

    keyboard = [
        [InlineKeyboardButton("🎥 ویدیو", callback_data=f"filetype_video_{video_index}"),
         InlineKeyboardButton("🎵 صوتی", callback_data=f"filetype_audio_{video_index}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"شما ویدیوی زیر را انتخاب کرده‌اید:\n\n🎥 {selected_video['title']}\n\nلطفاً نوع فایل را انتخاب کنید:",
                                  reply_markup=reply_markup)
    await query.answer()

# تابع انتخاب فرمت فایل
async def select_format(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    video_index = int(data.split("_")[2])
    selected_video = user_search_results[query.message.chat_id][video_index]

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
        await query.message.edit_text("❌ متاسفانه فرمت‌های قابل دانلود برای این ویدیو موجود نیست.")
        await query.answer()
        return

    keyboard = [
        [InlineKeyboardButton(f'{f["ext"]} {f["height"] if "height" in f else ""}', callback_data=f"download_{f['format_id']}_{video_index}") for f in formats]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(f"ویدیوی انتخابی: {selected_video['title']}\n\nلطفاً فرمت مورد نظر خود را انتخاب کنید:",
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

    # استفاده از yt-dlp برای دریافت لینک دانلود
    ydl_opts = {
        'format': format_id,
        'outtmpl': '%(id)s.%(ext)s',  # مسیر ذخیره فایل (در اینجا فقط لینک دانلود داده می‌شود)
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(selected_video['url'], download=False)
        download_link = result.get('url', None)

    # تبدیل لینک به لینک کوتاه (در صورت نیاز)
    if download_link:
        download_link = shorten_url(download_link)

    if download_link:
        await query.message.edit_text(f"✅ فایل آماده است!\n\n🎥 ویدیو: {selected_video['title']}\n🔗 لینک دانلود: {download_link}")
    else:
        await query.message.edit_text(f"❌ متاسفانه دانلود این ویدیو امکان‌پذیر نیست.")
    await query.answer()

# تابع تبدیل لینک به کوتاه
def shorten_url(url):
    try:
        response = requests.get(f'https://api.shrtco.de/v2/shorten?url={url}')
        if response.status_code == 201:
            return response.json()['result']['short_link']
        return url  # در صورت خطا، لینک اصلی باز می‌گردد
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
        return url

# اصلی‌ترین تابع
def main():
    application = Application.builder().token(TOKEN).build()

    # دستورات و دکمه‌ها
    application.add_handler(CommandHandler("start", send_welcome))
    application.add_handler(CommandHandler("search", search_video))
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(CallbackQueryHandler(choose_file_type, pattern='^video_\\d+$'))
    application.add_handler(CallbackQueryHandler(select_format, pattern='^filetype_(video|audio)_\\d+$'))
    application.add_handler(CallbackQueryHandler(send_download_link, pattern='^download_\\w+_\\d+$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_invalid_message))

    logger.info("ربات در حال اجراست...")
    application.run_polling()

if __name__ == '__main__':
    main()
