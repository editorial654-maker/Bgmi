#!/usr/bin/env python3
"""
Zeta Bot Launcher - Works without sudo (Railway/Termux compatible)
Run: python3 start.py
"""

import subprocess
import os
import sys

def run_command(cmd, description=None):
    """Run a command and print status"""
    if description:
        print(f"[*] {description}")
    
    result = os.system(cmd)
    if result != 0:
        print(f"❌ Command failed: {cmd}")
        return False
    return True

def detect_os():
    """Detect the operating system"""
    if os.path.exists('/data/data/com.termux/files/usr'):
        return 'termux'
    elif os.path.exists('/.dockerenv') or os.path.exists('/railway'):
        return 'railway'
    elif subprocess.run("which apt-get", shell=True, capture_output=True).returncode == 0:
        return 'debian'
    elif subprocess.run("which apk", shell=True, capture_output=True).returncode == 0:
        return 'alpine'
    return 'unknown'

def install_compiler():
    """Install C++ compiler based on OS (without sudo)"""
    os_type = detect_os()
    print(f"[+] Detected OS: {os_type}")
    
    if os_type == 'termux':
        print("[+] Installing clang for Termux...")
        run_command("pkg update -y", "Updating packages")
        run_command("pkg install clang -y", "Installing clang")
        return True
        
    elif os_type == 'railway' or os_type == 'debian':
        print("[+] Installing g++ for Debian/Railway...")
        # Railway runs as root, no sudo needed
        run_command("apt-get update -y", "Updating packages")
        run_command("apt-get install -y g++", "Installing g++")
        return True
        
    elif os_type == 'alpine':
        print("[+] Installing g++ for Alpine...")
        run_command("apk update", "Updating packages")
        run_command("apk add g++", "Installing g++")
        return True
        
    else:
        print("[!] Unknown OS. Please install g++ manually:")
        print("    Ubuntu/Debian: apt-get install g++ -y")
        print("    Termux: pkg install clang -y")
        print("    Alpine: apk add g++")
        return False

def main():
    print("=" * 50)
    print("🔥 ZETA BOT LAUNCHER 🔥")
    print("=" * 50)
    
    # Step 1: Check if compiler is available
    compiler = None
    if os.system("which g++ > /dev/null 2>&1") == 0:
        compiler = "g++"
    elif os.system("which clang++ > /dev/null 2>&1") == 0:
        compiler = "clang++"
    
    if not compiler:
        print("[!] No C++ compiler found!")
        print("[+] Attempting to install compiler...")
        if not install_compiler():
            sys.exit(1)
        
        # Re-check after installation
        if os.system("which g++ > /dev/null 2>&1") == 0:
            compiler = "g++"
        elif os.system("which clang++ > /dev/null 2>&1") == 0:
            compiler = "clang++"
        else:
            print("[!] Still no compiler found. Trying direct compile with available tools...")
            # Try to use cc if available
            if os.system("which cc > /dev/null 2>&1") == 0:
                compiler = "cc"
                print(f"[+] Found C compiler: {compiler}")
    
    if not compiler:
        print("❌ No compiler available! Exiting.")
        sys.exit(1)
    
    print(f"[+] Using compiler: {compiler}")
    
    # Step 2: Check if source file exists
    if not os.path.exists("bgmi.c"):
        print("❌ bgmi.c not found!")
        sys.exit(1)
    
    # Step 3: Compile the binary
    print("[+] Compiling bgmi_beast...")
    compile_cmd = f"{compiler} -O3 -pthread -std=c++11 -o bgmi_beast bgmi.c"
    
    if os.system(compile_cmd) != 0:
        print("❌ Compilation failed!")
        print("[*] Trying with relaxed flags...")
        # Try with fewer optimizations
        compile_cmd = f"{compiler} -O2 -pthread -o bgmi_beast bgmi.c"
        if os.system(compile_cmd) != 0:
            print("❌ Compilation still failing!")
            sys.exit(1)
    
    print("✅ Compilation successful!")
    
    # Step 4: Set execute permissions
    os.system("chmod +x bgmi_beast")
    
    # Step 5: Install Python dependencies
    print("[+] Installing Python dependencies...")
    os.system("pip3 install python-telegram-bot==20.7 requests --quiet 2>/dev/null || pip install python-telegram-bot==20.7 requests --quiet")
    
    # Step 6: Check if bot script exists
    if not os.path.exists("bgmibot.py"):
        print("❌ bgmibot.py not found!")
        sys.exit(1)
    
    # Step 7: Start the bot
    print("=" * 50)
    print("🚀 Starting Zo Bot...")
    print("=" * 50)
    os.system("python3 bgmibot.py")

if __name__ == "__main__":
    main()
