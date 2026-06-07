#!/usr/bin/env bash
cd "$(dirname "$0")"
echo -e "\033[96mLaunching Enhanced Drone Console v2...\033[0m"
echo -e "\033[2mConnecting to drone at 127.0.0.1:14550\033[0m"
echo ""
python3 enhanced_drone_console_v2.py
read -p "Press Enter to close..."
