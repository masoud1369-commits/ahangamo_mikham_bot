import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import speedtest
import os

# فعال‌سازی لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'  # توکن ربات تلگرام
YOUTUBE_API_KEY = 'AIzaSyBhwd2T6v4wSlEV69euIUfnUlrmknynS2g'  # کلید API YouTube

# نگه‌داری نتایج جستجوی اخیر برای هر کاربر
user_search_results = {}

# تابعی برای گرفتن سرعت اینترنت کاربر
def check_internet_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000  # تبدیل به مگابیت بر ثانیه
        ping = st.results.ping
        return download_speed, ping
    except Exception as e:
        logger.error(f"Speed test failed: {e}")
        return None, None

# دستور /start
async def send_welcome(update: Update, context: CallbackContext):
    logger.info("Handling /start command")
    keyboard = [
        [InlineKeyboardButton("شروع", callback_data='start')],
        [InlineKeyboardButton("راهنما", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "سلام! من ربات جستجوگر یوتیوبم! 😎\n"
        "با من می‌تونی ویدیوهای یوتیوب رو پیدا کنی و دانلود کنی. دکمه 'شروع' رو بزن! 🚀",
        reply_markup=reply_markup
    )

# دستور /help
async def send_help(update: Update, context: CallbackContext):
    logger.info("Handling /help command")
    help_text = (
        "دستورهای من 😜:\n\n"
        "1. /start: شروع به کار با من.\n"
        "2. /help: نمایش دستورالعمل‌های من.\n"
        "3. /search [نام ویدیو]: جستجو برای ویدیوها در یوتیوب.\n"
        "   - مثلا: /search گربه‌های بانمک 😹\n"
        "4. انتخاب یک ویدیو و دریافت لینک دانلود.\n"
        "5. آیا سرعت اینترنت و پینگت رو می‌خواهی ببینی؟ 🤔"
    )
    await update.message.reply_text(help_text)

# دستور /search
async def search_video(update: Update, context: CallbackContext):
    logger.info("Handling /search command")
    video_name = ' '.join(context.args) if context.args else None
    if not video_name:
        logger.warning("No video name provided in /search command")
        await update.message.reply_text("🤔 ای بابا! نام ویدیو رو فراموش کردی وارد کنی؟")
        return

    try:
        logger.info(f"Searching for video: {video_name}")
        response = requests.get("https://www.googleapis.com/youtube/v3/search", params={
            'part': 'snippet',
            'q': video_name,
            'key': YOUTUBE_API_KEY,
            'maxResults': 5  # محدود کردن تعداد نتایج به 5
        })

        if response.status_code != 200:
            logger.error(f"YouTube API request failed with status code {response.status_code}")
            await update.message.reply_text(f"😢 وای! یه مشکلی پیش اومد. وضعیت درخواست: {response.status_code}")
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
                user_search_results[update.message.chat_id] = video_results
                await display_search_results(update, context, video_results)
            else:
                await update.message.reply_text("😕 هیچی پیدا نکردیم! دوباره تلاش کن.")
        else:
            await update.message.reply_text("😔 هیچ ویدیویی پیدا نشد.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to YouTube API failed: {e}")
        await update.message.reply_text("🚫 مشکل در اتصال به YouTube API.")

# نمایش نتایج جستجو
async def display_search_results(update: Update, context: CallbackContext, video_results):
    logger.info("Displaying search results to user")
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {video['title']}", callback_data=f"video_{i}")] 
        for i, video in enumerate(video_results)
    ]
    keyboard.append([InlineKeyboardButton("🔄 جستجوی جدید", callback_data='new_search')])
    keyboard.append([InlineKeyboardButton("📤 اشتراک‌گذاری با دوستان", url="https://t.me/share/url?url=https://www.youtube.com/")])  # لینک اشتراک‌گذاری
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎥 ویدیوهای پیدا شده:\n\nلطفاً یک ویدیو رو انتخاب کن که دانلودش کنی! اگر خواستی با دوستات هم به اشتراک بذاری، دکمه رو بزن! 😎",
        reply_markup=reply_markup
    )

# ارسال لینک دانلود اصلاح‌شده با پیش‌نمایش
async def send_modified_link(update: Update, context: CallbackContext):
    query = update.callback_query
    try:
        video_index = int(query.data.split("_")[1])
        selected_video = user_search_results[query.message.chat_id][video_index]
        logger.info(f"User selected video: {selected_video['title']}")

        original_url = selected_video['url']
        modified_url = original_url.replace("youtube.com", "youtubepp.com")

        preview_text = (
            f"✅ ویدیو انتخابی شما: <b>{selected_video['title']}</b>\n\n"
            f"🔗 <a href='{original_url}'>نمایش ویدیو</a>"
        )
        await query.message.reply_text(preview_text, parse_mode="HTML")

        final_text = (
            f"✅ ویدیو شما: <b>{selected_video['title']}</b>\n\n"
            f"⬇️ روی لینک زیر بزنید تا وارد صفحه دانلود شوید:\n\n"
            f"🔗 <a href='{modified_url}'>{modified_url}</a>"
        )
        await query.message.reply_text(final_text, parse_mode="HTML")

        # از کاربر می‌خواهیم که آیا می‌خواهد سرعت اینترنت و پینگ خود را مشاهده کند یا خیر
        await ask_for_speed_check(query)

        await query.answer()

    except IndexError:
        logger.error("Invalid video selection.")
        await query.message.edit_text("❌ انتخاب نامعتبر، لطفاً دوباره تلاش کن.")
        await query.answer()

# از کاربر می‌خواهیم که آیا می‌خواهد سرعت اینترنت و پینگ را مشاهده کند یا خیر
async def ask_for_speed_check(query):
    keyboard = [
        [InlineKeyboardButton("بله", callback_data='yes_speed')],
        [InlineKeyboardButton("خیر", callback_data='no_speed')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "\n👨‍💻 آیا می‌خوای سرعت اینترنت و پینگت را مشاهده کنی؟"
         "ممکنه یمقدار طول بکشه! یکبار دکمه >بله< رو بزن و یکم صبور باش.\n\n"
         ,
        reply_markup=reply_markup
    )

# پیام تست سرعت 
async def handle_speed_check_response(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'yes_speed':
        download_speed, ping = check_internet_speed()
        if download_speed is not None and ping is not None:
            speed_message = (
                f"🌐 سرعت دانلود شما: {download_speed:.2f} Mbps\n"
                f"📶 پینگ: {ping} ms\n\n"
                "🚀 آقا، دقت کن! شاید این سرعت اینترنت شما به اندازه یه لاک‌پشت باشه، ولی یه روزی به همون سرعت می‌رسه که کیبوردت برات پرچم می‌زاره!\n\n"
                "🔮 احتمالا این شعر از مولانا به دردت می‌خوره:\n"
                "در دل شب نشسته‌ام با غم‌هایم\n"
                "دریغا که کار جهان تنها به خواب رفتن نیست.\n"
            )
            await query.message.reply_text(speed_message)
        else:
            await query.message.reply_text("متاسفانه نتونستم سرعت رو بگیرم. لطفا دوباره امتحان کن!")
    else:
        await query.message.reply_text("خیلی خوب، باشه! سراغ چیزهای دیگه میریم.")

# اجرای تابع handler برای Vercel
def handler(request):
    app = Application.builder().token(TOKEN).build()

    # ثبت دستورات
    app.add_handler(CommandHandler("start", send_welcome))
    app.add_handler(CommandHandler("help", send_help))
    app.add_handler(CommandHandler("search", search_video))

    # ثبت CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(send_modified_link, pattern=r"video_\d+"))
    app.add_handler(CallbackQueryHandler(handle_speed_check_response, pattern='yes_speed'))
    app.add_handler(CallbackQueryHandler(handle_speed_check_response, pattern='no_speed'))

    # اجرای برنامه به صورت سرورلس
    app.run_polling(drop_pending_updates=True)  # برای استفاده در Vercel لازم نیست polling را اجرا کنید

    return "Function executed successfully!"  # اینجا پاسخ دلخواه را برمی‌گردانیم
