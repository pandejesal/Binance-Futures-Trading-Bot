"""
Custom Exception Classes.

Defines the domain-specific exceptions used throughout the trading bot application
to handle validation, API, and network connectivity issues gracefully.
"""

class TradingBotError(Exception):
    """Base exception for all trading bot errors."""
    pass

class ConfigurationError(TradingBotError):
    """Raised when there is an issue with the environment configuration."""
    pass

class ValidationError(TradingBotError):
    """Raised when request parameters fail local pre-flight validation rules."""
    pass

class ExchangeConnectionError(TradingBotError):
    """Raised when there is a network-level connection failure or timeout."""
    pass

class ExchangeAPIError(TradingBotError):
    """
    Raised when the Binance API returns an error response (non-2xx status code).
    Contains the error code and message returned by the exchange.
    """
    def __init__(self, message: str, status_code: int, binance_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.binance_code = binance_code

    def __str__(self) -> str:
        return f"ExchangeAPIError (HTTP {self.status_code}, Code {self.binance_code}): {self.args[0]}"
