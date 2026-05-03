#!/usr/bin/env python3
"""
Zeta Bot Launcher - Auto installs compiler and runs bot
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
    elif subprocess.run("which apt-get", shell=True, capture_output=True).returncode == 0:
        return 'debian'
    elif subprocess.run("which yum", shell=True, capture_output=True).returncode == 0:
        return 'redhat'
    elif subprocess.run("which pacman", shell=True, capture_output=True).returncode == 0:
        return 'arch'
    return 'unknown'

def install_compiler():
    """Install C++ compiler based on OS"""
    os_type = detect_os()
    print(f"[+] Detected OS: {os_type}")
    
    if os_type == 'termux':
        print("[+] Installing clang for Termux...")
        run_command("pkg update -y", "Updating packages")
        run_command("pkg install clang -y", "Installing clang")
        return True
        
    elif os_type == 'debian':
        print("[+] Installing g++ for Debian/Ubuntu...")
        run_command("sudo apt-get update -y", "Updating packages")
        run_command("sudo apt-get install -y g++", "Installing g++")
        return True
        
    elif os_type == 'redhat':
        print("[+] Installing g++ for RHEL/CentOS...")
        run_command("sudo yum install -y gcc-c++", "Installing g++")
        return True
        
    elif os_type == 'arch':
        print("[+] Installing g++ for Arch...")
        run_command("sudo pacman -S --noconfirm gcc", "Installing gcc")
        return True
        
    else:
        print("[!] Unknown OS. Please install g++ manually:")
        print("    Ubuntu/Debian: sudo apt-get install g++ -y")
        print("    Termux: pkg install clang -y")
        print("    RHEL/CentOS: sudo yum install gcc-c++ -y")
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
        sys.exit(1)
    
    print("✅ Compilation successful!")
    
    # Step 4: Set execute permissions
    os.system("chmod +x bgmi_beast")
    
    # Step 5: Install Python dependencies
    print("[+] Installing Python dependencies...")
    os.system("pip3 install python-telegram-bot==20.7 requests --quiet")
    
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
