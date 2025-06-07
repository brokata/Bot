import sqlite3
from PIL import Image
from telebot import TeleBot
from io import BytesIO
import threading
import time
import logging
import requests
from telebot import TeleBot, types
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

# Telegram Bot Token
bot_token = "7643490329:AAFDxe-SopZ_sBUXNLCEf-xrH-pXxtkIP4U"  # Replace with your actual bot token
bot = TeleBot(telebot)

# User states to track the deposit process
user_states = {}

# List of admin user IDs
ADMIN_IDS = [1962908375]

# Item prices (key: item_id, value: price in $)
ITEM_PRICES = {
    "11": {"normal": 0.20, "reseller": 0.19},
    "22": {"normal": 0.39, "reseller": 0.37},
    "56": {"normal": 0.98, "reseller": 0.92},
    "86": {"normal": 1.16, "reseller": 1.04},
    "112": {"normal": 1.96, "reseller": 1.78},
    "172": {"normal": 2.29, "reseller": 2.05},
    "257": {"normal": 3.34, "reseller": 3.12},
    "343": {"normal": 4.49, "reseller": 3.95},
    "429": {"normal": 5.63, "reseller": 5.00},
    "514": {"normal": 6.67, "reseller": 5.91},
    "600": {"normal": 7.63, "reseller": 6.93},
    "706": {"normal": 9.00, "reseller": 8.20},
    "792": {"normal": 10.10, "reseller": 9.10},
    "878": {"normal": 11.30, "reseller": 10.00},
    "963": {"normal": 12.3, "reseller": 11.00},
    "1049": {"normal": 13.50, "reseller": 12.00},
    "1135": {"normal": 14.53, "reseller": 13.10},
    "1412": {"normal": 18.00, "reseller": 16.04},
    "1584": {"normal": 20.30, "reseller": 18.00},
    "1755": {"normal": 22.60, "reseller": 20.00},
    "2195": {"normal": 27.30, "reseller": 23.00},
    "2538": {"normal": 31.80, "reseller": 28.50},
    "3688": {"normal": 45.50, "reseller": 40.50},
    "5532": {"normal": 68.70, "reseller": 61.02},
    "9288": {"normal": 114.00, "reseller": 100.70},
    "10700": {"normal": 122.00, "reseller": 119.10},
    "Weekly": {"normal": 1.29, "reseller": 1.24},
    "2Weekly": {"normal": 2.58, "reseller": 2.48},
    "3Weekly": {"normal": 3.87, "reseller": 3.72},
    "4Weekly": {"normal": 5.16, "reseller": 4.96},
    "5Weekly": {"normal": 6.45, "reseller": 6.20},
    "Twilight": {"normal": 7.10, "reseller": 6.80},
}

ITEM_FF_PRICES = {
    "25": {"normal": 0.28, "reseller": 0.23},
    "100": {"normal": 0.9, "reseller": 0.82},
    "310": {"normal": 2.6, "reseller": 2.45},
    "520": {"normal": 4.25, "reseller": 4.09},
    "1060": {"normal": 8.25, "reseller": 8.02},
    "2180": {"normal": 16.57, "reseller": 16.18},
    "5600": {"normal": 43.00, "reseller": 40.05},
    "11500": {"normal": 84, "reseller": 82.42},
    "Weekly": {"normal": 1.5, "reseller": 1.40},
    "WeeklyLite": {"normal": 0.4, "reseller": 0.35},
    "Monthly": {"normal": 7.01, "reseller": 6.92},
    "Evo3D": {"normal": 0.6, "reseller": 0.60},
    "Evo7D": {"normal": 0.83, "reseller": 0.80},
    "Evo30D": {"normal": 2.35, "reseller": 2.2},
    "Levelpass": {"normal": 3.25, "reseller": 3.35},
    "Airdrop": {"normal": 1.25, "reseller": 1.25},
}

# Database setup
def init_db():
    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0,
            is_reseller INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Function to get user balance
def get_user_balance(user_id):
    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM balances WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# Function to update user balance
def update_user_balance(user_id, amount):
    current_balance = get_user_balance(user_id)
    new_balance = current_balance + amount
    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO balances (user_id, balance) VALUES (?, ?)', (user_id, new_balance))
    conn.commit()
    conn.close()

# Check if a user is a reseller
def is_reseller(user_id):
    try:
        conn = sqlite3.connect("user_balances.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_reseller FROM balances WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] == 1 if result else False
    except Exception as e:
        logging.error(f"Error checking reseller status for user {user_id}: {e}")
        return False       

# Set a user as a reseller
def add_reseller(user_id):
    conn = sqlite3.connect("user_balances.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO balances (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE balances SET is_reseller = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Unset a user as a reseller
def remove_reseller(user_id):
    conn = sqlite3.connect("user_balances.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO balances (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE balances SET is_reseller = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()        

# Command to set a user as a reseller
@bot.message_handler(commands=['addre'])
def add_reseller_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        target_user_id = int(message.text.split()[1])
        add_reseller(target_user_id)
        bot.reply_to(message, f"✅ User {target_user_id} is now a reseller.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Usage: /addre <user_id>")

# Command to unset a user as a reseller
@bot.message_handler(commands=['delre'])
def remove_reseller_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        target_user_id = int(message.text.split()[1])
        remove_reseller(target_user_id)
        bot.reply_to(message, f"✅ User {target_user_id} is no longer a reseller.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Usage: /delre <user_id>")

# Command to set item prices
def set_price_handler(message, item_prices):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        args = message.text.split()
        if len(args) != 4:
            bot.reply_to(message, "Usage: /set_price <item_id> <normal_price> <reseller_price>")
            return

        item_id = args[1]
        normal_price = float(args[2])
        reseller_price = float(args[3])

        if item_id in item_prices:
            item_prices[item_id]["normal"] = normal_price
            item_prices[item_id]["reseller"] = reseller_price
            bot.reply_to(message, f"✅ Prices updated for item {item_id}:\nNormal Price: ${normal_price}\nReseller Price: ${reseller_price}")
        else:
            bot.reply_to(message, f"Item ID {item_id} does not exist.")

    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid input. Please ensure you provide valid prices.")


@bot.message_handler(commands=['set_ml'])
def set_ml_handler(message):
    set_price_handler(message, ITEM_PRICES)

@bot.message_handler(commands=['set_ff'])
def set_ff_handler(message):
    set_price_handler(message, ITEM_FF_PRICES)

@bot.message_handler(commands=['allbal'])
def allbal_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    # Retrieve all user balances
    conn = sqlite3.connect('user_balances.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance FROM balances')
    results = cursor.fetchall()
    conn.close()

    # Prepare the data for the file
    file_content = "User  ID, Balance\n"
    for user_id, balance in results:
        file_content += f"{user_id}, {balance:.2f}\n"

    # Save the data to a file
    file_path = "user_balances.txt"
    with open(file_path, "w") as file:
        file.write(file_content)

    # Send the file to the admin
    with open(file_path, "rb") as file:
        bot.send_document(admin_id, file, caption="""Love You""")

    # Optionally, you can delete the file after sending
    os.remove(file_path)

# Command to add balance to a user
@bot.message_handler(commands=['addb'])
def addb_handler(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to use this command.")
        return

    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Usage: /addb <user_id> <amount>")
            return

        target_user_id = int(args[1])
        amount = float(args[2])

        if amount <= 0:
            bot.reply_to(message, "Amount must be greater than 0.")
            return

        update_user_balance(target_user_id, amount)
        bot.reply_to(message, f"✅ Added ${amount:.2f} to user {target_user_id}'s balance.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Invalid input. Please ensure you provide a valid user ID and amount.")

# Initialize the database
init_db()

# Function to handle the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    button1 = KeyboardButton('👤 Account')
    button2 = KeyboardButton('🎮 Game')
    button3 = KeyboardButton('💰 Deposit')
    markup.add(button1, button2, button3)
    bot.send_message(message.chat.id, "Welcome! How can I assist you today?", reply_markup=markup)

# Function to handle the 'Account' button press (Show balance)
@bot.message_handler(func=lambda message: message.text == '👤 Account')
def handle_account(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    user_balance = get_user_balance(chat_id)
    bot.send_message(chat_id, f"Name: {username}\nID: {user_id}\nBalance: ${user_balance:.2f} USD")

# Function to handle the 'Game' button press
@bot.message_handler(func=lambda message: message.text == '🎮 Game')
def handle_game(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button1 = KeyboardButton('Mobile Legends')
    button2 = KeyboardButton('Free Fire')
    button_back = KeyboardButton('Back')
    markup.add(button1, button2, button_back)
    bot.send_message(message.chat.id, "Select product category", reply_markup=markup)

# Function to handle the 'Back' button press
@bot.message_handler(func=lambda message: message.text == 'Back')
def handle_back(message):
    send_welcome(message)

# Function to handle 'Mobile Legends' game choice
@bot.message_handler(func=lambda message: message.text == 'Mobile Legends')
def handle_game_choice(message):
    user_id = message.from_user.id
    if is_reseller(user_id):
        product_list = "\n".join([f"{item_id} - {data['reseller']:.2f}" for item_id, data in ITEM_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Mobile Legends (Reseller)\n\n{product_list}\n\nExample format order:
 123456789 12345 Weekly
 userid serverid item""")
    else:
        product_list1 = "\n".join([f"{item_id} - ${data['normal']:.2f}" for item_id, data in ITEM_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Mobile Legends\n\n{product_list1}\n\nExample format order:
 123456789 12345 Weekly
 userid serverid item""")

# Function to handle 'Free Fire' game choice
@bot.message_handler(func=lambda message: message.text == 'Free Fire')
def handle_free_fire(message):
    user_id = message.from_user.id
    if is_reseller(user_id):
        product_list2 = "\n".join([f"{item_id} - {data['reseller']:.2f}" for item_id, data in ITEM_FF_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Mobile Legends (Reseller)\n\n{product_list2}\n\nExample format order:
 123456789 0 Weekly
 userid serverid item""")
    else:
        product_list3 = "\n".join([f"{item_id} - ${data['normal']:.2f}" for item_id, data in ITEM_FF_PRICES.items()])
        bot.send_message(message.chat.id, f"""Products List Mobile Legends\n\n{product_list3}\n\nExample format order:
 123456789 0 Weekly
 userid serverid item""")

# Handler for Button 3 ("💰 ដាក់ប្រាក់")
@bot.message_handler(func=lambda message: message.text == "💰 Deposit")
def button_3_handler(message):
    # Send a PNG image from the local file system
    with open("panha.JPG", "rb") as photo:  # Replace with your actual file path
        bot.send_photo(message.chat.id, photo, caption="សូមផ្ញើវិក្កយប័ត្រនៃការទូទាត់ប្រាក់មកកាន់ខ្ញុំ")

# Handler for receiving photos
@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    user_id = message.from_user.idusername = message.from_user.username or "Unknown"

    # Get the photo ID (largest resolution)
    photo_id = message.photo[-1].file_id

    # Notify the admins
    for admin_id in ADMIN_IDS:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        bot.send_message(admin_id, f" Add balance from @{username}\nUser ID: {user_id}")
        bot.send_photo(admin_id, photo_id)

    # Acknowledge the user
    bot.reply_to(message, "សូមរងចាំខ្ញុំនឹងដាក់ទឹកប្រាក់ជូនអ្នក🕚…")


# Buying
@bot.message_handler(func=lambda message: len(message.text.split()) == 3)
def buy_item_handler(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()

        # Extract server ID, zone ID, and item ID from the message
        try:
            server_id = int(args[0])
            zone_id = int(args[1])
            item_id = args[2]
        except ValueError:
            bot.send_message(message.chat.id, "Invalid server ID or zone ID. Please enter valid numbers.")
            return

        # Determine which price list to use based on zone_id
        price_list = ITEM_FF_PRICES if zone_id == 0 else ITEM_PRICES

        # Check if the item ID is valid and if the price is available
        if item_id not in price_list:
            bot.send_message(message.chat.id, f"Item ID {item_id} does not exist.")
            return

        # Determine the price based on user type (reseller or normal)
        price = price_list[item_id]["reseller"] if is_reseller(user_id) else price_list[item_id]["normal"]

        # Check user balance
        balance = get_user_balance(user_id)
        if balance < price:
            bot.send_message(message.chat.id, f"Insufficient balance. The item costs ${price:.2f}. Please add funds.")
            return

        # Validate Mobile Legends ID with API only if zone_id is not 0
        nickname = "Unknown"  # Default nickname
        if zone_id != 0:
            api_url = f"https://api.isan.eu.org/nickname/ml?id={server_id}&zone={zone_id}"
            try:
                response = requests.get(api_url)
                response.raise_for_status()  # Raise an error for bad responses
                data = response.json()
                if data.get("success"):
                    nickname = data.get("name", "unfinded")
                else:
                    bot.reply_to(message, "Wrong ID")
                    return
            except requests.RequestException as e:
                bot.send_message(message.chat.id, "Error validating ID MLBB. Please try again later.")
                logging.error(f"API request failed: {e}")
                return

        # Deduct price from balance
        update_user_balance(user_id, -price)

        # Notify the user
        bot.send_message(message.chat.id, f"New Order Successfully ❇️\nPlayer ID: {server_id}\nServer ID: {zone_id}\nNickname: {nickname}\nProduct: {item_id}\nStatus: Success ✅")

        group_1_id = -1002324595749 #MLBB
        group_4_id = -1002254587412 #FF
        if zone_id != 0:
            purchase_details = f"{server_id} {zone_id} {item_id}"
            send_group_message(group_1_id, purchase_details)
        else:
            purchase_details = f"{server_id} {zone_id} {item_id}"
            send_group_message(group_4_id, purchase_details)
       

        group_2_id = -1002422055998
        group_3_id = -1002422055998

        # Conditional message based on zone_id
        if zone_id != 0:
            buyer_info = f"New Order Sucessfully ❇️\nPlayer ID: {server_id}\nServer ID: {zone_id}\nNickname: {nickname}\nProduct: {item_id}\nStatus: Success ✅"
            send_group_message(group_2_id, buyer_info)  # Send to Group 2 if zone_id is not 0
        else:
            buyer_info = f"New Order Sucessfully ❇️\nPlayer ID: {server_id}\nServer ID: {zone_id}\nNickname: {nickname}\nProduct: {item_id}\nStatus: Success ✅"
            send_group_message(group_3_id, buyer_info)  # Send to Group 3 if zone_id is 0

    except Exception as e:
        bot.send_message(message.chat.id, f"An error occurred: {e}")
        logging.error(f"Error in buy_item_handler: {e}")

def send_group_message(group_id, message):
    try:
        bot.send_message(group_id, message)
    except Exception as e:
        logging.error(f"Failed to send message to group {group_id}: {e}")    

# Run the bot
if __name__ == "__main__":
    init_db()
    logging.info("Bot is running...")
    bot.infinity_polling()
