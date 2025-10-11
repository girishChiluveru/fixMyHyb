#!/usr/bin/env python3
"""
FixMyHyd Telegram Bot
Main entry point for the application
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import main

if __name__ == '__main__':
    main()