"""
Trading Bot Main Entry Point.

Allows the trading bot CLI to be run directly from inside the trading_bot directory.
Injects the directory into the Python path and delegates execution to bot.cli.
"""

import os
import sys

# Ensure current folder is on python path for importing bot modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from bot.cli import main

if __name__ == "__main__":
    sys.exit(main())
