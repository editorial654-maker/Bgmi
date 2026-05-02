#!/bin/bash

# Zeta Bot - Railway Launcher
echo "🔥 ZETA BOT - RAILWAY DEPLOYMENT 🔥"
echo "===================================="

# Navigate to working directory
cd /app || cd $HOME

# Check if g++ is installed
if ! command -v g++ &> /dev/null; then
    echo "❌ g++ not found! This shouldn't happen on Railway."
    exit 1
fi

echo "✅ Compiler found: $(g++ --version | head -1)"

# Compile the binary
echo "🔨 Compiling bgmi_beast from bgmi.c..."
g++ -O3 -pthread -std=c++11 -o bgmi_beast bgmi.c 2>&1

if [ $? -eq 0 ] && [ -f "bgmi_beast" ]; then
    echo "✅ Compilation successful"
    chmod +x bgmi_beast
    ls -la bgmi_beast
else
    echo "❌ Compilation failed"
    cat bgmi.c | head -20
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install python-telegram-bot==20.7

# Start the bot
echo "🚀 Starting Zo Bot..."
echo "===================================="
python3 bgmibot.py
