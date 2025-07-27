import telebot
import json
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db

# ----------------------
# 🔐 Firebase Config
# ----------------------

FIREBASE_REALTIME_DB = "https://bot-9dce9-default-rtdb.firebaseio.com/"

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': FIREBASE_REALTIME_DB
})

# ----------------------
# ⚙️ Bot Config
# ----------------------

BOT_TOKEN = "7722473597:AAE7sMdXDkfkhWWJoPLD4l79TBouucyMWwg"
ADMIN_ID = 6983955329
bot = telebot.TeleBot(BOT_TOKEN)

# ----------------------
# ✅ /start command
# ----------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎉 ស្វាគមន៍មកកាន់ Bot Boost TikTok Views\n\n📥 បញ្ជូន Link TikTok ដើម្បី boost!")

# ----------------------
# ✅ /boost command (user order)
# ----------------------

@bot.message_handler(commands=['boost'])
def boost(message):
    bot.send_message(message.chat.id, "📎 សូមផ្ញើ Link TikTok:")
    bot.register_next_step_handler(message, handle_boost_link)

def handle_boost_link(message):
    user_id = message.from_user.id
    tiktok_link = message.text

    # ✅ Example: deduct balance 0.5
    user_ref = db.reference(f"balances/{user_id}")
    old_balance = user_ref.get() or 0

    cost = 0.5
    if old_balance < cost:
        bot.send_message(message.chat.id, "❌ អត់លុយគ្រប់។ សូមទំនាក់ទំនង Admin!")
        return

    new_balance = old_balance - cost
    user_ref.set(new_balance)

    # ✅ Save order to Firebase
    order = {
        "user_id": user_id,
        "link": tiktok_link,
        "views": 1000,
        "price": cost,
        "time": str(datetime.now())
    }

    res = requests.post(FIREBASE_REALTIME_DB + "/orders.json", data=json.dumps(order))
    if res.status_code == 200:
        bot.send_message(message.chat.id, f"✅ Boost order របស់អ្នកត្រូវបានបញ្ចូល!\n📊 ចំនួនប្រាក់នៅសល់: ${new_balance:.2f}")
    else:
        bot.send_message(message.chat.id, "❌ បរាជ័យក្នុងការបញ្ចូល order!")

# ----------------------
# ✅ /addb command (Admin Only)
# ----------------------

@bot.message_handler(commands=['addb'])
def add_balance(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "🚫 អ្នកមិនមែនជាអ្នកគ្រប់គ្រងទេ!")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.send_message(message.chat.id, "❌ Format: /addb <userid> <money>")
        return

    target_id = args[1]
    try:
        amount = float(args[2])
    except ValueError:
        bot.send_message(message.chat.id, "❌ សូមបញ្ចូលចំនួនលុយត្រឹមត្រូវ!")
        return

    ref = db.reference(f"balances/{target_id}")
    old_balance = ref.get() or 0
    new_balance = old_balance + amount
    ref.set(new_balance)

    bot.send_message(message.chat.id, f"✅ បន្ថែម ${amount} ទៅ user {target_id}\n💰 Balance now: ${new_balance:.2f}")

# ----------------------
# ✅ /balance command
# ----------------------

@bot.message_handler(commands=['balance'])
def balance(message):
    user_id = message.from_user.id
    bal = db.reference(f"balances/{user_id}").get() or 0
    bot.send_message(message.chat.id, f"💰 ប្រាក់នៅសល់របស់អ្នក: ${bal:.2f}")

# ----------------------
# ✅ Run bot
# ----------------------

bot.polling()
