#!/usr/bin/env python3
"""
Simple starter script for Polymarket Insider Detection Bot

Usage: python start_bot.py
"""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the bot
from polymarket_insider_bot.main import main

if __name__ == '__main__':
    main()
