import os, json, asyncio
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- ENV SAFETY ----------
def env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value

TOKEN = env("BOT_TOKEN")
ADMIN_ID = int(env("ADMIN_ID"))
GOOGLE_CREDS = env("GOOGLE_CREDENTIALS")

# ---------- GOOGLE SHEETS ----------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(GOOGLE_CREDS)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Admissions").sheet1

# ---------- BOT LOGIC ----------
user_data = {}

async def start(update, context):
    user_data[update.effective_user.id] = {}
    await update.message.reply_text("Welcome! What's your name?")

async def message_handler(update, context):
    if not update.message or not update.message.text:
        return

    uid = update.effective_user.id
    text = update.message.text.strip()

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

        row = [
            data["name"],
            data["phone"],
            data["course"],
            data["city"],
            datetime.now().strftime("%d-%m-%Y %H:%M")
        ]

        # Prevent event-loop blocking
        await context.application.run_in_executor(
            None,
            lambda: sheet.append_row(row)
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "New Lead:\n"
                f"Name: {data['name']}\n"
                f"Phone: {data['phone']}\n"
                f"Course: {data['course']}\n"
                f"City: {data['city']}"
            )
        )

        await update.message.reply_text("Thanks! Our team will contact you shortly.")
        del user_data[uid]

# ---------- START APP ----------
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

app.run_polling()
