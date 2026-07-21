"""
Utility Helpers Module.

Provides pure functions for formatting, masking credentials, converting timestamps,
and supplying uniform terminal UX feedback symbols.
"""

from datetime import datetime
from typing import Optional

def mask_api_key(api_key: Optional[str]) -> str:
    """
    Masks a sensitive API key to prevent it from being exposed in logs or console output.
    Returns something like 'ABCD********XYZ'.
    """
    if not api_key:
        return ""
    api_key = api_key.strip()
    if len(api_key) > 8:
        return f"{api_key[:4]}********{api_key[-3:]}"
    return "********"

def format_price(price: Optional[float], decimals: int = 4) -> str:
    """
    Formats a numeric price value to a consistent string representation with set decimals.
    """
    if price is None:
        return "N/A"
    try:
        return f"{float(price):.{decimals}f}"
    except (TypeError, ValueError):
        return str(price)

def format_timestamp(timestamp_ms: Optional[int]) -> str:
    """
    Translates a millisecond epoch timestamp from the exchange into a human-readable local time.
    """
    if not timestamp_ms or timestamp_ms <= 0:
        return "N/A"
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "N/A"

def get_success_symbol() -> str:
    """Returns a success emoji or symbol for CLI rendering."""
    return "✓"

def get_failure_symbol() -> str:
    """Returns a failure emoji or symbol for CLI rendering."""
    return "✗"

def get_info_symbol() -> str:
    """Returns an informational emoji or symbol for CLI rendering."""
    return "ℹ"
