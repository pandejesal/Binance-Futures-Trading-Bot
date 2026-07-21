"""
Order Service Layer Module.

Responsible for translating user inputs into the specific payloads required by the
Binance Futures API, dispatching requests through the cryptographic client layer,
normalizing order execution responses, and mapping exchange errors to custom exceptions.
"""

import logging
from typing import Any, Dict, Optional

from bot.client import BinanceClient
from bot.exceptions import ExchangeAPIError, TradingBotError
from bot.validators import validate_order_inputs

class OrderService:
    """
    Handles higher-level order preparation, transmission, response parsing, and error mapping
    for Binance Futures orders.
    """

    def __init__(self, client: BinanceClient) -> None:
        """
        Initializes the OrderService with a configured BinanceClient.
        """
        self.logger = logging.getLogger(__name__)
        self.client = client

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Prepares, signs, and executes an order on the Binance Futures Testnet.

        Args:
            symbol: Trading pair (e.g., BTCUSDT).
            side: Order side (BUY, SELL).
            order_type: Order type (MARKET, LIMIT, STOP_MARKET).
            quantity: Order quantity.
            price: Order price (required for LIMIT orders).
            stop_price: Trigger price (required for STOP_MARKET orders).

        Returns:
            A normalized execution dictionary containing:
            - orderId: Unique exchange identifier
            - status: Current order status (e.g., NEW, FILLED)
            - executedQty: Total quantity filled
            - avgPrice: Average transaction price
            - origQty: Original order quantity
            - symbol: Trading pair
            - side: Order side
            - type: Order type

        Raises:
            ValidationError: If inputs are invalid.
            ExchangeConnectionError: For network timeouts or connection failures.
            ExchangeAPIError: When the exchange returns a standard API error.
            TradingBotError: For mapped exchange-specific business failures (e.g., margin).
        """
        # Validate inputs first (safety pre-flight)
        v_symbol, v_side, v_type, v_qty, v_price, v_stop_price = validate_order_inputs(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )

        # Build payload according to Binance Futures specifications
        payload: Dict[str, Any] = {
            "symbol": v_symbol,
            "side": v_side,
            "type": v_type,
            "quantity": v_qty,
        }

        if v_type == "LIMIT":
            payload["price"] = v_price
            payload["timeInForce"] = "GTC"  # Good Till Cancelled is the industry default
        elif v_type == "STOP_MARKET":
            payload["stopPrice"] = v_stop_price

        self.logger.info(
            f"Pre-flight validation passed. Dispatching {v_side} {v_type} "
            f"order for {v_qty} {v_symbol}..."
        )

        try:
            # Send authenticated POST request to /fapi/v1/order
            raw_response = self.client.send_request(
                method="POST",
                endpoint="/fapi/v1/order",
                params=payload,
                authenticated=True
            )
            
            # Normalize and return response
            return self._normalize_response(raw_response, v_type)

        except ExchangeAPIError as e:
            # Map common Binance error codes into descriptive custom exception messages
            mapped_error = self._map_binance_error(e)
            self.logger.error(f"Order placement failed on exchange: {mapped_error}")
            raise mapped_error from e

    def _normalize_response(self, raw: Dict[str, Any], order_type: str) -> Dict[str, Any]:
        """
        Extracts execution fields and standardizes the exchange response structure.
        """
        # Extract direct fields
        order_id = raw.get("orderId", "N/A")
        status = raw.get("status", "N/A")
        symbol = raw.get("symbol", "N/A")
        side = raw.get("side", "N/A")
        orig_qty = float(raw.get("origQty", 0.0))
        executed_qty = float(raw.get("executedQty", 0.0))

        # Calculate average filled price
        # Binance returns 'avgPrice' directly in some cases, or we can look at cumQty & cumQuote
        avg_price = 0.0
        avg_price_str = raw.get("avgPrice")
        
        if avg_price_str is not None and float(avg_price_str) > 0:
            avg_price = float(avg_price_str)
        else:
            cum_qty = float(raw.get("cumQty", 0.0))
            cum_quote = float(raw.get("cumQuote", 0.0))
            if cum_qty > 0:
                avg_price = cum_quote / cum_qty
            else:
                # Fallback to limit price or 0.0
                avg_price = float(raw.get("price", 0.0))

        normalized = {
            "orderId": order_id,
            "status": status,
            "executedQty": executed_qty,
            "avgPrice": avg_price,
            "origQty": orig_qty,
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "clientOrderId": raw.get("clientOrderId", "N/A"),
            "updateTime": raw.get("updateTime", 0)
        }

        self.logger.info(
            f"Successfully processed order! Order ID: {order_id} | Status: {status} | "
            f"Executed Qty: {executed_qty} | Avg Price: {avg_price}"
        )
        return normalized

    def _map_binance_error(self, error: ExchangeAPIError) -> ExchangeAPIError:
        """
        Intercepts raw ExchangeAPIErrors and returns an exception with a more
        helpful context-specific message, mapping well-known Binance error codes.
        """
        code = error.binance_code
        msg = error.args[0]
        custom_message = msg

        # Mapped from official Binance Futures API specifications
        error_map = {
            -1013: "Order rejected: Quantity/price fails filters. The quantity might be "
                   "below minimum required contracts, or price increments are incorrect.",
            -1102: "Mandatory parameter is missing or malformed. Double-check CLI inputs.",
            -1111: "Precision exceeded for quantity or price. Format float values to fewer decimals.",
            -2015: "Authentication failed: Invalid API Key, API Secret, or IP restriction. "
                   "Verify keys in your .env configuration.",
            -2019: "Insufficient margin/balance. Please deposit USDT into your Binance Futures Testnet account.",
            -2027: "Header 'X-MBX-APIKEY' is missing or invalid. Check client initialization.",
            -4013: "Order price is too far from current market price (Price protection triggered)."
        }

        if code in error_map:
            custom_message = f"{error_map[code]} (Exchange Code: {code}, Details: {msg})"

        return ExchangeAPIError(
            message=custom_message,
            status_code=error.status_code,
            binance_code=code
        )
