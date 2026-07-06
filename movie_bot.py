
import os
import sys
import asyncio
import json
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Unicode fix for Windows terminal
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Bot tokenini bu yerga qo'ying (yoki .env fayldan o'qishingiz mumkin)
TELEGRAM_BOT_TOKEN = "8049497888:AAFA2O4fhGFk1WvJJT6nrkUEYmSR_whJEN4"

# Foydalanuvchi holatlari
ADMIN_LOGIN, ADMIN_PASSWORD, ADMIN_ADD_CODE, ADMIN_ADD_VIDEO = range(4)
USER_GET_CODE = 0

# Ma'lumotlar bazasi (oddiy JSON fayl)
DATA_FILE = "movie_data.json"

# Ma'lumotlar bazasini yuklash
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"movies": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"movies": {}}

# Ma'lumotlar bazasini saqlash
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Botni ishga tushirish
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Kino botiga xush kelibsiz!\n"
        "Kino olish uchun unikal kodni yuboring.\n\n"
        
    )
    return USER_GET_CODE

# Foydalanuvchi kod yuborganida
async def user_get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    data = load_data()
    
    if code in data["movies"]:
        video_info = data["movies"][code]
        await update.message.reply_text(f"Kino topildi: {video_info.get('title', 'Nomi yoq')}")
        await update.message.reply_video(video_info["file_id"])
    else:
        await update.message.reply_text("Bunday kod bilan kino topilmadi!")
    
    return USER_GET_CODE

# Admin login bosqichi
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Admin paneliga kirish uchun loginni kiriting:")
    return ADMIN_LOGIN

# Loginni tekshirish
async def admin_check_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    login = update.message.text.strip()
    if login == "root":
        context.user_data["login_attempted"] = True
        await update.message.reply_text("Login to'g'ri! Endi parolni kiriting:")
        return ADMIN_PASSWORD
    else:
        await update.message.reply_text("Login noto'g'ri! Qaytadan urinib ko'ring yoki /start orqali foydalanuvchi rejimiga o'ting.")
        return ADMIN_LOGIN

# Parolni tekshirish
async def admin_check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if password == "admin":
        await update.message.reply_text(
            "Admin paneliga muvaffaqiyatli kirdingiz!\n\n"
            "Yangi kino qo'shish uchun yangi kodni kiriting:\n"
            "(Bekor qilish uchun /cancel buyrug'ini ishlating)"
        )
        return ADMIN_ADD_CODE
    else:
        await update.message.reply_text("Parol noto'g'ri! Qaytadan urinib ko'ring yoki /start orqali foydalanuvchi rejimiga o'ting.")
        return ADMIN_LOGIN

# Kod qo'shish bosqichi
async def admin_add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    data = load_data()
    
    if code in data["movies"]:
        await update.message.reply_text(f"'{code}' kodi allaqachon ishlatilgan! Boshqa kod kiriting:")
        return ADMIN_ADD_CODE
    
    context.user_data["new_movie_code"] = code
    await update.message.reply_text(f"Kod '{code}' qabul qilindi! Endi kinoni (videoni) yuboring:")
    return ADMIN_ADD_VIDEO

# Videoni qabul qilish va saqlash
async def admin_add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text("Iltimos, faqat video yuboring!")
        return ADMIN_ADD_VIDEO
    
    code = context.user_data["new_movie_code"]
    video = update.message.video
    data = load_data()
    
    data["movies"][code] = {
        "file_id": video.file_id,
        "title": video.file_name or f"Kino {code}",
        "added_by": update.effective_user.id
    }
    
    save_data(data)
    await update.message.reply_text(f"Kino muvaffaqiyatli qo'shildi!\nKod: {code}\n\nYana kino qo'shish uchun yangi kod kiriting yoki /start orqali chiqib ketishingiz mumkin.")
    return ADMIN_ADD_CODE

# Bekor qilish
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Amal bekor qilindi. /start orqali qaytadan boshlang.")
    return ConversationHandler.END

def main():
    print("Kino bot ishga tushmoqda...")
    
    # Asyncio loop ni sozlash
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Application yaratish
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Admin uchun ConversationHandler
    admin_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^admin$'), admin_start)],
        states={
            ADMIN_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_login)],
            ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)],
            ADMIN_ADD_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_code)],
            ADMIN_ADD_VIDEO: [MessageHandler(filters.VIDEO, admin_add_video)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Foydalanuvchi uchun ConversationHandler
    user_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            USER_GET_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_get_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Handlerlarni qo'shish
    application.add_handler(admin_conv_handler)
    application.add_handler(user_conv_handler)
    
    print("Kino bot ishga tushdi!")
    application.run_polling()

if __name__ == "__main__":
    main()
