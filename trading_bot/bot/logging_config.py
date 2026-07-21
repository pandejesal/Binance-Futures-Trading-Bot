"""
Logging Configuration Module.

Sets up a dual-handler logging system that writes detailed debug traces to a file
and clean, high-level informational logs to the terminal. It includes a custom
obfuscating formatter to ensure API credentials are never written to disk or console.
"""

import logging
import os
import sys
from typing import Optional
from bot.utils import mask_api_key

class ObfuscatingFormatter(logging.Formatter):
    """
    Custom logging Formatter that automatically intercepts and obfuscates
    sensitive API keys and secrets in log messages.
    """

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None) -> None:
        super().__init__(fmt, datefmt)
        # Retrieve potential sensitive variables from environment
        self._api_key = os.getenv("BINANCE_API_KEY", "")
        self._api_secret = os.getenv("BINANCE_API_SECRET", "")

        # Prepare masked representations
        self._masked_key = mask_api_key(self._api_key)

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats the log record and replaces any sensitive credentials in the message.
        """
        # Save the original message and args
        orig_msg = record.msg
        orig_args = record.args

        # Format message first so string interpolation happens
        formatted = super().format(record)

        # Apply obfuscation to the formatted string
        if self._api_secret and self._api_secret in formatted:
            formatted = formatted.replace(self._api_secret, "[REDACTED_SECRET]")
        
        if self._api_key and self._api_key in formatted:
            formatted = formatted.replace(self._api_key, self._masked_key)

        return formatted

def setup_logging(log_filename: str = "trading_bot.log") -> logging.Logger:
    """
    Initializes and configures the root logger with dual handlers:
    1. A File Handler writing detailed traces at the DEBUG level to log_filename.
    2. A Stream Handler writing clean logs at the INFO level to sys.stdout.

    Args:
        log_filename: The path of the file where logs will be written.

    Returns:
        The configured root Logger instance.
    """
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates if re-initialized
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Set root level to DEBUG so both handlers can receive up to DEBUG level messages
    root_logger.setLevel(logging.DEBUG)

    # 1. File Handler (Detailed logs at DEBUG level)
    file_formatter = ObfuscatingFormatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create logs directory if it's specified in a relative path and doesn't exist
    log_dir = os.path.dirname(log_filename)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 2. Terminal stdout Handler (Clean logs at INFO level and above)
    console_formatter = ObfuscatingFormatter(
        fmt="%(levelname)s: %(message)s"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    return root_logger
