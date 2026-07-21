"""
Unit Tests for Binance Futures Trading Bot.

Tests parameter validator scenarios, input validation bounds, and payload serializations
for MARKET, LIMIT, and STOP_MARKET orders using standard unittest libraries and mocks.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure trading_bot root is in Python path for test execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.exceptions import ValidationError, ExchangeAPIError
from bot.validators import validate_order_inputs
from bot.orders import OrderService
from bot.client import BinanceClient


class TestValidators(unittest.TestCase):
    """TestSuite for checking pre-flight validation logic."""

    def test_successful_market_validation(self) -> None:
        """Verifies that correct MARKET order parameters validate and sanitize cleanly."""
        sym, side, otype, qty, price, stop = validate_order_inputs(
            symbol="btcusdt ",
            side=" buy ",
            order_type=" market ",
            quantity="0.005"
        )
        self.assertEqual(sym, "BTCUSDT")
        self.assertEqual(side, "BUY")
        self.assertEqual(otype, "MARKET")
        self.assertEqual(qty, 0.005)
        self.assertIsNone(price)
        self.assertIsNone(stop)

    def test_successful_limit_validation(self) -> None:
        """Verifies that correct LIMIT order parameters validate and sanitize cleanly."""
        sym, side, otype, qty, price, stop = validate_order_inputs(
            symbol="ethusdt",
            side="SELL",
            order_type="LIMIT",
            quantity=1.5,
            price=3200.50
        )
        self.assertEqual(sym, "ETHUSDT")
        self.assertEqual(side, "SELL")
        self.assertEqual(otype, "LIMIT")
        self.assertEqual(qty, 1.5)
        self.assertEqual(price, 3200.50)
        self.assertIsNone(stop)

    def test_successful_stop_market_validation(self) -> None:
        """Verifies that correct STOP_MARKET order parameters validate and sanitize cleanly."""
        sym, side, otype, qty, price, stop = validate_order_inputs(
            symbol="SOLUSDT",
            side="BUY",
            order_type="STOP_MARKET",
            quantity=10,
            stop_price=145.25
        )
        self.assertEqual(sym, "SOLUSDT")
        self.assertEqual(side, "BUY")
        self.assertEqual(otype, "STOP_MARKET")
        self.assertEqual(qty, 10.0)
        self.assertIsNone(price)
        self.assertEqual(stop, 145.25)

    def test_invalid_symbol(self) -> None:
        """Verifies that invalid symbols raise ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="", side="BUY", order_type="MARKET", quantity=1.0)
        self.assertIn("Symbol must be a non-empty string", str(ctx.exception))

    def test_invalid_side(self) -> None:
        """Verifies that invalid order sides raise ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="BTCUSDT", side="HOLD", order_type="MARKET", quantity=1.0)
        self.assertIn("Invalid order side 'HOLD'", str(ctx.exception))

    def test_invalid_order_type(self) -> None:
        """Verifies that invalid order types raise ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="BTCUSDT", side="BUY", order_type="TRAILING_STOP", quantity=1.0)
        self.assertIn("Invalid order type 'TRAILING_STOP'", str(ctx.exception))

    def test_invalid_quantity(self) -> None:
        """Verifies that negative or non-numeric quantities raise ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity=-0.5)
        self.assertIn("Quantity must be strictly positive", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity="abc")
        self.assertIn("Quantity must be a valid numeric value", str(ctx.exception))

    def test_limit_missing_price(self) -> None:
        """Verifies that a LIMIT order without a price raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="BTCUSDT", side="BUY", order_type="LIMIT", quantity=1.0)
        self.assertIn("Price is required for LIMIT orders", str(ctx.exception))

    def test_limit_negative_price(self) -> None:
        """Verifies that a LIMIT order with a negative price raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="BTCUSDT", side="BUY", order_type="LIMIT", quantity=1.0, price=-500)
        self.assertIn("Price must be strictly positive", str(ctx.exception))

    def test_stop_market_missing_stop_price(self) -> None:
        """Verifies that a STOP_MARKET order without a stop_price raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            validate_order_inputs(symbol="BTCUSDT", side="BUY", order_type="STOP_MARKET", quantity=1.0)
        self.assertIn("Stop Price is required for STOP_MARKET orders", str(ctx.exception))


class TestOrderServicePayloadMapping(unittest.TestCase):
    """TestSuite for mapping logic, verifying that OrderService compiles correct payloads."""

    def setUp(self) -> None:
        # Create mock client
        self.mock_client = MagicMock(spec=BinanceClient)
        self.service = OrderService(self.mock_client)

    def test_market_order_payload(self) -> None:
        """Tests that MARKET order compiles exact payload key-values."""
        # Setup mock return value
        self.mock_client.send_request.return_value = {
            "orderId": 887766,
            "status": "FILLED",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "origQty": "0.015",
            "executedQty": "0.015",
            "avgPrice": "62000.0",
            "clientOrderId": "custom_id_123",
            "updateTime": 1718900000000
        }

        result = self.service.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.015
        )

        # Verify send_request argument payload
        self.mock_client.send_request.assert_called_once_with(
            method="POST",
            endpoint="/fapi/v1/order",
            params={
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "MARKET",
                "quantity": 0.015
            },
            authenticated=True
        )

        # Verify parsed execution dictionary
        self.assertEqual(result["orderId"], 887766)
        self.assertEqual(result["status"], "FILLED")
        self.assertEqual(result["avgPrice"], 62000.0)
        self.assertEqual(result["executedQty"], 0.015)

    def test_limit_order_payload(self) -> None:
        """Tests that LIMIT order compiles exact payload key-values."""
        self.mock_client.send_request.return_value = {
            "orderId": 991122,
            "status": "NEW",
            "symbol": "ETHUSDT",
            "side": "SELL",
            "origQty": "2.0",
            "executedQty": "0.0",
            "price": "3500.00",
            "avgPrice": "0.0",
            "clientOrderId": "limit_id_99",
            "updateTime": 1718900100000
        }

        result = self.service.place_order(
            symbol="ETHUSDT",
            side="SELL",
            order_type="LIMIT",
            quantity=2.0,
            price=3500.0
        )

        self.mock_client.send_request.assert_called_once_with(
            method="POST",
            endpoint="/fapi/v1/order",
            params={
                "symbol": "ETHUSDT",
                "side": "SELL",
                "type": "LIMIT",
                "quantity": 2.0,
                "price": 3500.0,
                "timeInForce": "GTC"
            },
            authenticated=True
        )

        self.assertEqual(result["orderId"], 991122)
        self.assertEqual(result["status"], "NEW")
        self.assertEqual(result["avgPrice"], 3500.0)  # should fall back to price if executedQty is 0
        self.assertEqual(result["executedQty"], 0.0)

    def test_stop_market_order_payload(self) -> None:
        """Tests that STOP_MARKET order compiles exact payload key-values."""
        self.mock_client.send_request.return_value = {
            "orderId": 554433,
            "status": "NEW",
            "symbol": "SOLUSDT",
            "side": "BUY",
            "origQty": "5.0",
            "executedQty": "0.0",
            "stopPrice": "150.0",
            "avgPrice": "0.0",
            "clientOrderId": "stop_id_88",
            "updateTime": 1718900200000
        }

        result = self.service.place_order(
            symbol="SOLUSDT",
            side="BUY",
            order_type="STOP_MARKET",
            quantity=5.0,
            stop_price=150.0
        )

        self.mock_client.send_request.assert_called_once_with(
            method="POST",
            endpoint="/fapi/v1/order",
            params={
                "symbol": "SOLUSDT",
                "side": "BUY",
                "type": "STOP_MARKET",
                "quantity": 5.0,
                "stopPrice": 150.0
            },
            authenticated=True
        )

        self.assertEqual(result["orderId"], 554433)
        self.assertEqual(result["status"], "NEW")


class TestUtils(unittest.TestCase):
    """TestSuite for verifying formatting, masking, and CLI UX symbols."""

    def test_mask_api_key(self) -> None:
        """Verifies that sensitive keys are masked correctly and edge cases are handled."""
        from bot.utils import mask_api_key
        self.assertEqual(mask_api_key(""), "")
        self.assertEqual(mask_api_key(None), "")
        self.assertEqual(mask_api_key("abc"), "********")
        self.assertEqual(mask_api_key("1234567890"), "1234********890")

    def test_format_price(self) -> None:
        """Verifies that float, string, and None prices are formatted as expected."""
        from bot.utils import format_price
        self.assertEqual(format_price(None), "N/A")
        self.assertEqual(format_price(12.34567), "12.3457")
        self.assertEqual(format_price("12.34567"), "12.3457")
        self.assertEqual(format_price("not-a-number"), "not-a-number")

    def test_format_timestamp(self) -> None:
        """Verifies that millisecond timestamps are converted to readable date formats."""
        from bot.utils import format_timestamp
        self.assertEqual(format_timestamp(None), "N/A")
        self.assertEqual(format_timestamp(-100), "N/A")
        # 1718900000000 is 2024-06-20 approximately
        formatted = format_timestamp(1718900000000)
        self.assertNotEqual(formatted, "N/A")
        self.assertTrue(formatted.startswith("2024-06"))


if __name__ == "__main__":
    unittest.main()
