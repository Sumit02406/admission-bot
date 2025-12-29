import os, json, asyncio, logging, time
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)

# -------- ENV ----------
def need(name):
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

TOKEN = need("BOT_TOKEN")
ADMIN_ID = int(need("ADMIN_ID"))
SPREADSHEET_ID = need("SPREADSHEET_ID")
CREDS_RAW = need("GOOGLE_CREDENTIALS")

# -------- GOOGLE SAFE CONNECT ----------
def connect_sheet():
    for attempt in range(1, 6):
        try:
            logging.info(f"Connecting to Google Sheets (attempt {attempt})")
            creds = Credentials.from_service_account_info(
                json.loads(CREDS_RAW),
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            gc = gspread.authorize(creds)
            return gc.open_by_key(SPREADSHEET_ID).sheet1
        except Exception as e:
            logging.error(f"Google connection failed: {e}")
            time.sleep(10)
    raise RuntimeError("Google Sheets unreachable after 5 attempts")

sheet = connect_sheet()

# -------- BOT ----------
users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_user.id] = {}
    await update.message.reply_text("Welcome! What's your name?")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    uid = update.effective_user.id
    text = update.message.text.strip()

    if uid not in users:
        await update.message.reply_text("Type /start to begin.")
        return

    u = users[uid]

    if "name" not in u:
        u["name"] = text
        await update.message.reply_text("Your phone number?")
        return

    if "phone" not in u:
        u["phone"] = text
        await update.message.reply_text("Which course are you interested in?")
        return

    if "course" not in u:
        u["course"] = text
        await update.message.reply_text("Your city?")
        return

    u["city"] = text

    row = [u["name"], u["phone"], u["course"], u["city"],
           datetime.now().strftime("%d-%m-%Y %H:%M")]

    loop = asyncio.get_running_loop()
    for _ in range(5):
        try:
            await loop.run_in_executor(None, lambda: sheet.append_row(row))
            break
        except Exception as e:
            logging.error(f"Append failed: {e}")
            await asyncio.sleep(5)

    await context.bot.send_message(
        ADMIN_ID,
        f"New Lead\n\nName: {u['name']}\nPhone: {u['phone']}\nCourse: {u['course']}\nCity: {u['city']}"
    )

    await update.message.reply_text("Thanks! Our team will contact you shortly.")
    del users[uid]

# -------- SELF HEALING LOOP ----------
def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling(close_loop=False)

while True:
    try:
        run_bot()
    except Exception as e:
        logging.error(f"FATAL ERROR – restarting in 10s: {e}")
        time.sleep(10)
