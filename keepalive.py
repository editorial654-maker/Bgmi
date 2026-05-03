#!/usr/bin/env python3
"""
GitHub Codespaces Keep Alive Script
Prevents auto-shutdown due to inactivity
Run: python3 keepalive.py
"""

import time
import os
import subprocess
import threading
import random

print("=" * 50)
print("🔥 KEEP ALIVE FOR CODESPACES 🔥")
print("=" * 50)
print("This will prevent inactivity shutdown")
print("Press Ctrl+C to stop\n")

def keep_github_active():
    """Simulates activity to prevent shutdown"""
    while True:
        # Create dummy file activity
        os.system('touch /tmp/keepalive 2>/dev/null')
        time.sleep(300)  # Every 5 minutes

def run_bot():
    """Run your bot"""
    os.system('python3 bgmibot.py')

# Start keep-alive thread
keep_thread = threading.Thread(target=keep_github_active, daemon=True)
keep_thread.start()

# Run the bot
print("[+] Starting bot with keep-alive...")
run_bot()
