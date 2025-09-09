# pip install python-telegram-bot==20.7 requests yt_dlp

import logging, requests, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime
import yt_dlp

BOT_TOKEN = "8424006252:AAEfpUuM8EuWovVPPBjLkG-fNZcTn3ukClU"
logging.basicConfig(level=logging.INFO)

tracking = {}
waiting_for_note = {}
current_mode = {}  # lưu user đang ở chế độ nào

# ========== MENU CHÍNH ==========
main_menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔎 Lấy UID Facebook")],
        [KeyboardButton("🎥 Tải video TikTok")],
        [KeyboardButton("🎬 Tải video Facebook")],
        [KeyboardButton("▶️ Tải video YouTube")]
    ],
    resize_keyboard=True
)

# ========== FUNCTION ==========
def check_facebook_status(url: str):
    try:
        r = requests.get(url, timeout=10)
        return "LIVE" if r.status_code == 200 else "DIE"
    except:
        return "DIE"

def format_message(uid, name, status, note="Chưa có"):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return (
        f"🔔UID: {uid}\n"
        f"🤷‍♂️Name: {name}\n"
        f"🍀Tình trạng : {status}\n"
        f"📒Note: {note}\n"
        f"⏰Time: {now}"
    )

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Xin chào! Chọn chức năng bên dưới:", reply_markup=main_menu)

# Khi user chọn menu
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    if text == "🔎 Lấy UID Facebook":
        current_mode[user_id] = "uid"
        await update.message.reply_text("📌 Gửi link Facebook để lấy UID.")
    elif text == "🎥 Tải video TikTok":
        current_mode[user_id] = "tiktok"
        await update.message.reply_text("📌 Gửi link TikTok cần tải.")
    elif text == "🎬 Tải video Facebook":
        current_mode[user_id] = "fbvideo"
        await update.message.reply_text("📌 Gửi link video Facebook cần tải.")
    elif text == "▶️ Tải video YouTube":
        current_mode[user_id] = "youtube"
        await update.message.reply_text("📌 Gửi link YouTube cần tải.")
    else:
        await handle_input(update, context)

# Xử lý input theo chế độ
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    mode = current_mode.get(user_id)

    if mode == "uid":
        # Giả sử convert link fb -> UID
        uid = "1597790867"
        name = "Hùng Đoàn"
        status = check_facebook_status(text)

        tracking[uid] = {"link": text, "name": name, "chat_id": update.message.chat_id, "note": "Chưa có"}

        keyboard = [
            [InlineKeyboardButton("👉 Theo dõi", callback_data=f"watch|{uid}|{name}")],
            [InlineKeyboardButton("⛔ Dừng", callback_data=f"stop|{uid}")],
            [InlineKeyboardButton("📝 Ghi chú", callback_data=f"note|{uid}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(format_message(uid, name, status), reply_markup=reply_markup)

    elif mode in ["tiktok", "fbvideo", "youtube"]:
        await download_video(update, text, mode)

# Tải video (TikTok, FB, YTB)
async def download_video(update: Update, url: str, mode: str):
    await update.message.reply_text("⏳ Đang tải video...")

    try:
        ydl_opts = {"format": "mp4", "outtmpl": "%(id)s.%(ext)s"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info["url"]
            title = info.get("title", "video")

        await update.message.reply_text(f"✅ Video: {title}\n📥 {video_url}")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi tải video: {str(e)}")

# Callback cho Theo dõi / Ghi chú
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]

    if action == "watch":
        uid, name = data[1], data[2]
        tracking[uid]["watching"] = True
        await query.edit_message_text(f"✅ UID {uid} đang được theo dõi 24/24")
        asyncio.create_task(track_link(uid, context))

    elif action == "stop":
        uid = data[1]
        if uid in tracking and tracking[uid].get("watching"):
            tracking[uid]["watching"] = False
            await query.edit_message_text(f"⛔ Đã dừng theo dõi UID {uid}")
        else:
            await query.edit_message_text(f"❌ UID {uid} chưa theo dõi")

    elif action == "note":
        uid = data[1]
        user_id = query.from_user.id
        waiting_for_note[user_id] = {"uid": uid}
        await query.edit_message_text(f"✍️ Nhập ghi chú cho UID {uid}:")

async def track_link(uid, context: ContextTypes.DEFAULT_TYPE):
    link = tracking[uid]["link"]
    name = tracking[uid]["name"]
    chat_id = tracking[uid]["chat_id"]
    last_status = None
    while uid in tracking and tracking[uid].get("watching"):
        status = check_facebook_status(link)
        if status != last_status:
            msg = format_message(uid, name, status, tracking[uid].get("note", "Chưa có"))
            await context.bot.send_message(chat_id, msg)
            last_status = status
        await asyncio.sleep(30)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(CallbackQueryHandler(button))
    print("🤖 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
