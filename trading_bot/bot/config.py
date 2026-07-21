"""
Configuration Management Module.

Handles loading of environment variables from .env files with multiple path searches,
validates that keys are provided and do not contain obvious default placeholder strings,
and provides a clean interface for other modules to access configuration.
"""

import os
from typing import Optional, Set
from bot.exceptions import ConfigurationError

# Load environment variables on module load
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manual fallback .env parser if python-dotenv is not installed/loaded yet
    for env_path in [".env", "trading_bot/.env", "../.env"]:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            os.environ[key.strip()] = val.strip().strip('"').strip("'")
            except Exception:
                pass

class AppConfig:
    """
    AppConfig retrieves, verifies, and provides access to environment configuration variables.
    """
    
    def __init__(self) -> None:
        self.api_key: str = os.getenv("BINANCE_API_KEY", "").strip()
        self.api_secret: str = os.getenv("BINANCE_API_SECRET", "").strip()
        self.base_url: str = os.getenv("TESTNET_URL", "https://testnet.binancefuture.com").strip()

    def verify(self) -> None:
        """
        Validates that required Binance API credentials are set in the environment
        and are not default placeholder strings.

        Raises:
            ConfigurationError: If keys are missing, empty, or set to placeholder values.
        """
        if not self.api_key:
            raise ConfigurationError(
                "BINANCE_API_KEY is not defined in the environment. "
                "Please configure it in your .env file."
            )
        if not self.api_secret:
            raise ConfigurationError(
                "BINANCE_API_SECRET is not defined in the environment. "
                "Please configure it in your .env file."
            )

        placeholders: Set[str] = {
            "your_api_key_here",
            "your_api_secret_here",
            "MY_BINANCE_API_KEY",
            "MY_BINANCE_API_SECRET",
            "MY_GEMINI_API_KEY",
            "GEMINI_API_KEY",
            "MY_APP_URL",
            ""
        }

        if self.api_key in placeholders:
            raise ConfigurationError(
                "BINANCE_API_KEY contains an invalid placeholder or empty string. "
                "Please update it with your actual Binance Testnet API key."
            )
        if self.api_secret in placeholders:
            raise ConfigurationError(
                "BINANCE_API_SECRET contains an invalid placeholder or empty string. "
                "Please update it with your actual Binance Testnet API secret."
            )

# Create a global config instance for singleton access
config = AppConfig()
