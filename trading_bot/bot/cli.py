"""
Command-Line Interface (CLI) Entry Point.

Builds the CLI parser, executes local parameter verification, interacts with the OrderService,
displays formatted summary cards to the console, and implements robust error handling with tracebacks
written to log files while showing user-friendly instructions on the terminal.
"""

import argparse
import logging
import sys
import traceback
from typing import List, Optional

from bot import verify_config, ConfigurationError
from bot.client import BinanceClient
from bot.exceptions import ValidationError, ExchangeConnectionError, ExchangeAPIError
from bot.logging_config import setup_logging
from bot.orders import OrderService
from bot.validators import validate_order_inputs
from bot.utils import (
    format_price,
    format_timestamp,
    get_success_symbol,
    get_failure_symbol,
    get_info_symbol
)

# ANSI Escape Sequences for terminal coloring (safe for all systems)
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_CYAN = "\033[96m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

def print_header(title: str, color: str = COLOR_CYAN) -> None:
    """Helper to print a uniform visual console separator header with color."""
    print(f"{color}{COLOR_BOLD}" + "=" * 60 + COLOR_RESET)
    print(f"{color}{COLOR_BOLD}{title.center(60)}{COLOR_RESET}")
    print(f"{color}{COLOR_BOLD}" + "=" * 60 + COLOR_RESET)

def main(args_list: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point function.

    Args:
        args_list: Optional list of argument strings (useful for unit tests/simulation).

    Returns:
        int: Return status code (0 for success, 1 for failure).
    """
    # 1. Setup dual-handler logging. Write all detailed trace/debug logs to trading_bot.log
    logger = setup_logging("trading_bot.log")
    logger.info("Application starting...")

    # 2. Build the command-line argument parser
    parser = argparse.ArgumentParser(
        description="Production-grade Binance Futures Testnet (USDT-M) Trading CLI Bot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Trading pair symbol (e.g., BTCUSDT, ETHUSDT)"
    )
    parser.add_argument(
        "--side",
        type=str,
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order execution side (BUY or SELL)"
    )
    parser.add_argument(
        "--type",
        type=str,
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"],
        help="Order execution execution type (MARKET, LIMIT, or STOP_MARKET)"
    )
    parser.add_argument(
        "--quantity",
        type=float,
        required=True,
        help="Order asset size (must be strictly positive)"
    )
    parser.add_argument(
        "--price",
        type=float,
        default=None,
        help="Execution target price. Mandatory for LIMIT orders."
    )
    parser.add_argument(
        "--stop-price",
        type=float,
        default=None,
        help="Trigger stop price. Mandatory for STOP_MARKET orders."
    )

    # Parse inputs (uses sys.argv if args_list is None)
    parsed = parser.parse_args(args_list)

    # Convert values to correct capitalization
    raw_symbol = parsed.symbol
    raw_side = parsed.side.upper() if parsed.side else ""
    raw_type = parsed.type.upper() if parsed.type else ""
    raw_qty = parsed.quantity
    raw_price = parsed.price
    raw_stop_price = parsed.stop_price

    # 3. Print Request Summary to standard output (as requested)
    print_header("ORDER REQUEST SUMMARY", COLOR_CYAN)
    print(f"  {COLOR_BOLD}Symbol:{COLOR_RESET}      {raw_symbol.upper()}")
    print(f"  {COLOR_BOLD}Side:{COLOR_RESET}        {raw_side}")
    print(f"  {COLOR_BOLD}Order Type:{COLOR_RESET}  {raw_type}")
    print(f"  {COLOR_BOLD}Quantity:{COLOR_RESET}    {raw_qty}")
    if raw_price is not None:
        print(f"  {COLOR_BOLD}Limit Price:{COLOR_RESET} {format_price(raw_price)} USDT")
    if raw_stop_price is not None:
        print(f"  {COLOR_BOLD}Stop Price:{COLOR_RESET}  {format_price(raw_stop_price)} USDT")
    print(f"{COLOR_CYAN}" + "=" * 60 + COLOR_RESET)
    print(f"{COLOR_YELLOW}{get_info_symbol()} Validating execution parameters locally...{COLOR_RESET}")

    try:
        # Verify that environment file is filled and configured correctly
        verify_config()

        # Run local parameter pre-flight validation
        validated = validate_order_inputs(
            symbol=raw_symbol,
            side=raw_side,
            order_type=raw_type,
            quantity=raw_qty,
            price=raw_price,
            stop_price=raw_stop_price
        )
        
        symbol_v, side_v, type_v, qty_v, price_v, stop_price_v = validated
        logger.info(
            f"Pre-flight parameters passed: {side_v} {type_v} for {qty_v} contracts of {symbol_v}"
        )

        # Initialize network components
        print(f"{COLOR_YELLOW}{get_info_symbol()} Connecting to Binance Futures Testnet...{COLOR_RESET}")
        client = BinanceClient()
        service = OrderService(client=client)

        # Transmit and execute order
        print(f"{COLOR_YELLOW}{get_info_symbol()} Dispatching order payload to exchange...{COLOR_RESET}")
        execution = service.place_order(
            symbol=symbol_v,
            side=side_v,
            order_type=type_v,
            quantity=qty_v,
            price=price_v,
            stop_price=stop_price_v
        )

        # 4. Display polished transaction card on success
        header_text = f"{get_success_symbol()} ORDER PLACED SUCCESSFULLY"
        print_header(header_text, COLOR_GREEN)
        print(f"  {COLOR_BOLD}Order ID:{COLOR_RESET}      {execution['orderId']}")
        print(f"  {COLOR_BOLD}Status:{COLOR_RESET}        {execution['status']}")
        print(f"  {COLOR_BOLD}Executed Qty:{COLOR_RESET}  {execution['executedQty']} (of {execution['origQty']})")
        print(f"  {COLOR_BOLD}Average Price:{COLOR_RESET} {format_price(execution['avgPrice'])} USDT")
        print(f"  {COLOR_BOLD}Symbol/Side:{COLOR_RESET}   {execution['symbol']} / {execution['side']}")
        print(f"  {COLOR_BOLD}Type/ClientID:{COLOR_RESET} {execution['type']} / {execution['clientOrderId']}")
        
        timestamp_ms = execution['updateTime']
        if timestamp_ms > 0:
            print(f"  {COLOR_BOLD}Timestamp:{COLOR_RESET}     {format_timestamp(timestamp_ms)}")
        
        print(f"{COLOR_GREEN}" + "=" * 60 + COLOR_RESET)
        print(f"{COLOR_GREEN}💡 Success details and payloads successfully recorded in trading_bot.log{COLOR_RESET}")
        logger.info(f"CLI successful execution completed for order ID: {execution['orderId']}")
        return 0

    except ValidationError as e:
        logger.warning(f"Local Pre-flight validation rejected parameters: {e}")
        header_text = f"{get_failure_symbol()} LOCAL VALIDATION ERROR"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}Reason:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 60 + COLOR_RESET)
        print(f"{COLOR_RED}💡 Review argument parameters. Trace history saved to trading_bot.log.{COLOR_RESET}")
        return 1

    except ConfigurationError as e:
        logger.error(f"Environment configuration mismatch: {e}")
        header_text = f"{get_failure_symbol()} CONFIGURATION ERROR"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}Reason:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 60 + COLOR_RESET)
        print(f"{COLOR_RED}💡 Fix environment settings in .env before executing CLI orders.{COLOR_RESET}")
        return 1

    except ExchangeConnectionError as e:
        logger.error(f"Network connectivity failure: {e}")
        logger.debug(traceback.format_exc())
        header_text = f"{get_failure_symbol()} NETWORK CONNECTION FAILURE"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}Reason:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 60 + COLOR_RESET)
        print(f"{COLOR_RED}💡 Check internet connections or testnet exchange endpoints status.{COLOR_RESET}")
        return 1

    except ExchangeAPIError as e:
        logger.error(f"Exchange refused request: {e}")
        logger.debug(traceback.format_exc())
        header_text = f"{get_failure_symbol()} EXCHANGE API REFUSED REQUEST"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}HTTP Code:{COLOR_RESET} {e.status_code}")
        print(f"  {COLOR_BOLD}Error Code:{COLOR_RESET} {e.binance_code}")
        print(f"  {COLOR_BOLD}Message:{COLOR_RESET} {e.args[0]}")
        print(f"{COLOR_RED}" + "=" * 60 + COLOR_RESET)
        print(f"{COLOR_RED}💡 Correct transaction configurations. Check account balance on testnet.{COLOR_RESET}")
        return 1

    except Exception as e:
        # Catch unexpected developer errors, write traceback to log file, and display neat exit warning
        logger.critical(f"Unhandled general exception occurred: {e}", exc_info=True)
        header_text = f"{get_failure_symbol()} CRITICAL BOT EXCEPTION"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}An unexpected system error occurred:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 60 + COLOR_RESET)
        print(f"{COLOR_RED}💡 Technical details have been logged with complete traceback in trading_bot.log{COLOR_RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
