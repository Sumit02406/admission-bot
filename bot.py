import os, json, asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

TOKEN = os.environ["8283743685:AAGqGvD54t---tXlNlt0DIspU3P_6kWfsl8"]
ADMIN_ID = int(os.environ["5550293914"])

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)
sheet = client.open("Admissions").sheet1

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {}
    await update.message.reply_text("Welcome! What's your name?")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if uid not in user_data:
        await update.message.reply_text("Type /start to begin.")
        return

    data = user_data[uid]

    if "name" not in data:
        data["name"] = text
        await update.message.reply_text("Your phone number?")
    elif "phone" not in data:
        data["phone"] = text
        await update.message.reply_text("Which course are you interested in?")
    elif "course" not in data:
        data["course"] = text
        await update.message.reply_text("Your city?")
    elif "city" not in data:
        data["city"] = text

        sheet.append_row([
            data["name"], data["phone"],
            data["course"], data["city"],
            datetime.now().strftime("%d-%m-%Y %H:%M")
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New Lead:\nName: {data['name']}\nPhone: {data['phone']}\nCourse: {data['course']}\nCity: {data['city']}"
        )

        await update.message.reply_text("Thanks! Our team will contact you shortly.")
        del user_data[uid]

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
