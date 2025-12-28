from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

TOKEN = "8283743685:AAGqGvD54t---tXlNlt0DIspU3P_6kWfsl8"
ADMIN_ID = 5550293914   # replace with your Telegram numeric id

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Admissions").sheet1

user_data = {}

def start(update, context):
    user_data[update.effective_user.id] = {}
    update.message.reply_text("Welcome! What's your name?")

def message_handler(update, context):
    uid = update.effective_user.id
    text = update.message.text

    if uid not in user_data:
        update.message.reply_text("Type /start to begin.")
        return

    data = user_data[uid]

    if "name" not in data:
        data["name"] = text
        update.message.reply_text("Your phone number?")
    elif "phone" not in data:
        data["phone"] = text
        update.message.reply_text("Which course are you interested in?")
    elif "course" not in data:
        data["course"] = text
        update.message.reply_text("Your city?")
    elif "city" not in data:
        data["city"] = text

        sheet.append_row([
            data["name"], data["phone"],
            data["course"], data["city"],
            datetime.now().strftime("%d-%m-%Y %H:%M")
        ])

        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New Lead:\nName: {data['name']}\nPhone: {data['phone']}\nCourse: {data['course']}\nCity: {data['city']}"
        )

        update.message.reply_text("Thanks! Our team will contact you shortly.")
        del user_data[uid]

updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

updater.start_polling()
updater.idle()
