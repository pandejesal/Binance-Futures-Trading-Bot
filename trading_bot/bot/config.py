"""
Configuration Management Module.

Handles loading of environment variables from .env files with multiple path searches,
validates that keys are provided and do not contain obvious default placeholder strings,
and provides a clean interface for other modules to access configuration.
"""

import os
import sys
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

    def set_credentials(self, api_key: str, api_secret: str) -> None:
        """Sets API credentials dynamically in memory and environment."""
        if api_key:
            self.api_key = api_key.strip()
            os.environ["BINANCE_API_KEY"] = self.api_key
        if api_secret:
            self.api_secret = api_secret.strip()
            os.environ["BINANCE_API_SECRET"] = self.api_secret

    def reload(self) -> None:
        """Reloads credentials from os.environ."""
        self.api_key = os.getenv("BINANCE_API_KEY", "").strip()
        self.api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    def verify(self, interactive_prompt: bool = True) -> None:
        """
        Validates that required Binance API credentials are set in the environment.
        If interactive_prompt is True and credentials are missing, prompts the user to enter them once.

        Raises:
            ConfigurationError: If keys are missing, empty, or set to placeholder values.
        """
        self.reload()

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

        # Prompt interactively if missing/placeholder in interactive CLI mode
        if interactive_prompt and (not self.api_key or self.api_key in placeholders or not self.api_secret or self.api_secret in placeholders):
            if sys.stdin.isatty():
                print("\n\033[93m🔑 Binance API Credentials not found or placeholder detected.\033[0m")
                if not self.api_key or self.api_key in placeholders:
                    entered_key = input("\033[1mEnter Binance Testnet API Key: \033[0m").strip()
                    if entered_key:
                        self.set_credentials(entered_key, self.api_secret)
                if not self.api_secret or self.api_secret in placeholders:
                    entered_secret = input("\033[1mEnter Binance Testnet API Secret: \033[0m").strip()
                    if entered_secret:
                        self.set_credentials(self.api_key, entered_secret)
                
                # Ask to save to .env
                if self.api_key and self.api_secret and self.api_key not in placeholders and self.api_secret not in placeholders:
                    save_env = input("\033[96mSave credentials to .env file for future runs? (y/n) [default y]: \033[0m").strip().lower()
                    if save_env in ("", "y", "yes"):
                        try:
                            env_content = f"BINANCE_API_KEY={self.api_key}\nBINANCE_API_SECRET={self.api_secret}\nTESTNET_URL=https://testnet.binancefuture.com\n"
                            with open(".env", "w", encoding="utf-8") as f:
                                f.write(env_content)
                            print("\033[92m✓ Credentials saved to .env!\033[0m\n")
                        except Exception as e:
                            print(f"\033[91mCould not write to .env: {e}\033[0m\n")

        if not self.api_key or self.api_key in placeholders:
            raise ConfigurationError(
                "BINANCE_API_KEY is not defined in environment. "
                "Specify --api-key / -k flag or configure it in .env"
            )
        if not self.api_secret or self.api_secret in placeholders:
            raise ConfigurationError(
                "BINANCE_API_SECRET is not defined in environment. "
                "Specify --api-secret / -s flag or configure it in .env"
            )

# Create a global config instance for singleton access
config = AppConfig()
