#!/usr/bin/env python3
"""
Simple Zeta Bot Launcher
Just gives chmod +x to bgmi_beast and runs the bot
Run: python3 run.py
"""

import os
import sys

def main():
    print("=" * 40)
    print("🔥 ZETA BOT LAUNCHER 🔥")
    print("=" * 40)
    
    # Step 1: Give execute permission to bgmi_beast
    if os.path.exists("bgmi_beast"):
        print("[+] Setting execute permission on bgmi_beast...")
        os.system("chmod +x bgmi_beast")
        print("✅ Permission set!")
    else:
        print("⚠️ bgmi_beast not found!")
        print("   Make sure the binary exists in current directory")
    
    # Step 2: Check if bot script exists
    if not os.path.exists("bgmibot.py"):
        print("❌ bgmibot.py not found!")
        sys.exit(1)
    
    # Step 3: Run the bot
    print("[+] Starting Zo Bot...")
    print("=" * 40)
    os.system("python3 bgmibot.py")

if __name__ == "__main__":
    main()
