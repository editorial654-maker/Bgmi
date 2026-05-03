#!/usr/bin/env python3
"""
One-liner setup - Just compile and run
Run: python3 start.py
"""

import subprocess
import os

def main():
    print("🔥 Compiling bgmi_beast...")
    
    # Determine compiler
    compiler = "clang++" if os.system("which clang++ > /dev/null 2>&1") == 0 else "g++"
    
    # Compile
    result = os.system(f"{compiler} -O3 -pthread -std=c++11 -o bgmi_beast bgmi.c && chmod +x bgmi_beast")
    
    if result == 0:
        print("✅ Compilation successful!")
        print("🚀 Starting bot...")
        os.system("python3 bgmibot.py")
    else:
        print("❌ Compilation failed!")

if __name__ == "__main__":
    main()
