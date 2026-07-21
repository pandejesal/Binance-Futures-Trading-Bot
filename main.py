"""
Root Main Application Entry Point.

Allows the trading bot CLI to be run directly from the root of the project.
Injects the trading_bot directory into the Python path and delegates execution to bot.cli.
"""

import os
import sys

# Ensure trading_bot folder is on python path for importing bot modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "trading_bot")))

from bot.cli import main

if __name__ == "__main__":
    sys.exit(main())
