"""
Binance Futures Trading Bot Package.

This package contains modules for placing orders on the Binance Futures Testnet (USDT-M)
using a custom REST client, cryptographic signing, robust validators, and structured logging.
"""

from bot.exceptions import ConfigurationError
from bot.config import config

def verify_config() -> None:
    """
    Verifies that the required Binance API credentials are set in the environment
    and are not default placeholder strings. Delegates to the singleton AppConfig instance.

    Raises:
        ConfigurationError: If keys are missing, empty, or set to placeholder values.
    """
    config.verify()

