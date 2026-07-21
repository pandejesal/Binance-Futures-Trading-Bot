"""
Parameter Validation Module.

Provides pre-flight checks on order input parameters (symbol, side, type, quantity,
price, and stop_price) before committing to any network I/O.
"""

from typing import Any, Dict, Optional, Tuple

from bot.exceptions import ValidationError

def validate_order_inputs(
    symbol: Any,
    side: Any,
    order_type: Any,
    quantity: Any,
    price: Optional[Any] = None,
    stop_price: Optional[Any] = None
) -> Tuple[str, str, str, float, Optional[float], Optional[float]]:
    """
    Validates order input parameters. Automatically coerces types and converts
    casing where appropriate.

    Args:
        symbol: The trading pair symbol (e.g., 'btcusdt').
        side: The order side ('BUY' or 'SELL').
        order_type: The order type ('MARKET', 'LIMIT', 'STOP_MARKET').
        quantity: The quantity of contract/asset to order.
        price: Required for LIMIT orders.
        stop_price: Required for STOP_MARKET orders.

    Returns:
        Tuple: Validated and sanitized (symbol, side, order_type, quantity, price, stop_price).

    Raises:
        ValidationError: If any of the inputs fail business logic validation rules.
    """
    # 1. Validate and sanitize Symbol
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValidationError("Symbol must be a non-empty string (e.g. 'BTCUSDT').")
    sanitized_symbol = symbol.strip().upper()

    # 2. Validate Side
    if not isinstance(side, str):
        raise ValidationError("Order side must be a string (BUY or SELL).")
    sanitized_side = side.strip().upper()
    if sanitized_side not in ("BUY", "SELL"):
        raise ValidationError(f"Invalid order side '{side}'. Must be strictly BUY or SELL.")

    # 3. Validate Order Type
    if not isinstance(order_type, str):
        raise ValidationError("Order type must be a string (MARKET, LIMIT, or STOP_MARKET).")
    sanitized_type = order_type.strip().upper()
    if sanitized_type not in ("MARKET", "LIMIT", "STOP_MARKET"):
        raise ValidationError(
            f"Invalid order type '{order_type}'. Supported types are MARKET, LIMIT, or STOP_MARKET."
        )

    # 4. Validate Quantity
    try:
        float_quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a valid numeric value. Received: {quantity}")

    if float_quantity <= 0:
        raise ValidationError(f"Quantity must be strictly positive. Received: {float_quantity}")

    # 5. Validate Price (required for LIMIT)
    float_price: Optional[float] = None
    if sanitized_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            float_price = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price must be a valid numeric value. Received: {price}")
        if float_price <= 0:
            raise ValidationError(f"Price must be strictly positive for LIMIT orders. Received: {float_price}")
    elif price is not None:
        # If price is provided for non-limit orders, validate it anyway but raise warning or keep it
        try:
            float_price = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price must be a valid numeric value. Received: {price}")

    # 6. Validate Stop Price (required for STOP_MARKET)
    float_stop_price: Optional[float] = None
    if sanitized_type == "STOP_MARKET":
        if stop_price is None:
            raise ValidationError("Stop Price is required for STOP_MARKET orders.")
        try:
            float_stop_price = float(stop_price)
        except (TypeError, ValueError):
            raise ValidationError(f"Stop Price must be a valid numeric value. Received: {stop_price}")
        if float_stop_price <= 0:
            raise ValidationError(
                f"Stop Price must be strictly positive for STOP_MARKET orders. Received: {float_stop_price}"
            )
    elif stop_price is not None:
        try:
            float_stop_price = float(stop_price)
        except (TypeError, ValueError):
            raise ValidationError(f"Stop Price must be a valid numeric value. Received: {stop_price}")

    return sanitized_symbol, sanitized_side, sanitized_type, float_quantity, float_price, float_stop_price
