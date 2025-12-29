import os, json, asyncio, logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)

def need(name):
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing env var: {name}")
    return val

TOKEN = need("BOT_TOKEN")
ADMIN_ID = int(need("ADMIN_ID"))
SPREADSHEET_ID = need("SPREADSHEET_ID")
CREDS_RAW = need("GOOGLE_CREDENTIALS")

# ---- GOOGLE AUTH ----
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_info = json.loads(CREDS_RAW)
creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
gc = gspread.authorize(creds)

# ⚠ DO NOT use gc.open("Admissions")
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# ---- BOT ----
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

    row = [
        u["name"],
        u["phone"],
        u["course"],
        u["city"],
        datetime.now().strftime("%d-%m-%Y %H:%M")
    ]

    loop = asyncio.get_running_loop()
    try:
    await loop.run_in_executor(None, lambda: sheet.append_row(row))
except Exception as e:
    print("Google Sheet error:", e)

    await context.bot.send_message(
        ADMIN_ID,
        f"New Lead\n\n"
        f"Name: {u['name']}\n"
        f"Phone: {u['phone']}\n"
        f"Course: {u['course']}\n"
        f"City: {u['city']}"
    )

    await update.message.reply_text("Thanks! Our team will contact you shortly.")
    del users[uid]

import time

def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling(close_loop=False)

while True:
    try:
        run_bot()
    except Exception as e:
        print("FATAL ERROR — restarting in 5 seconds:", e)
        time.sleep(5)
