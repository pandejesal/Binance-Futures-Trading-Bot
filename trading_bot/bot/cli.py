"""
Command-Line Interface (CLI) Entry Point.

Builds the CLI parser, supports both direct flag execution and an interactive terminal menu/wizard,
interacts with the OrderService, displays formatted summary cards and tables to the console, and
implements robust error handling with tracebacks written to log files.
"""

import argparse
import logging
import os
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

# ANSI Escape Sequences for terminal coloring
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_CYAN = "\033[96m"
COLOR_MAGENTA = "\033[95m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

ASCII_BANNER = f"""{COLOR_CYAN}{COLOR_BOLD}
   ____  _                                 ______ ______ 
  / __ )(_)___  ____ _____  ________ _____/ ____// ____/ 
 / __  / / __ \\/ __ `/ __ \\/ ___/ _ `/ ___/ /_   / /    
/ /_/ / / / / / /_/ / / / / /__/  __/ /__/ __/  / /___   
/_____/_/_/ /_/\\__,_/_/ /_/\\___/\\___/\\___/_/     \\____/   
                                                         
   Binance Futures (USDT-M) Testnet CLI Trading Bot
{COLOR_RESET}"""

def print_header(title: str, color: str = COLOR_CYAN) -> None:
    """Helper to print a uniform visual console separator header with color."""
    print(f"{color}{COLOR_BOLD}" + "=" * 65 + COLOR_RESET)
    print(f"{color}{COLOR_BOLD}{title.center(65)}{COLOR_RESET}")
    print(f"{color}{COLOR_BOLD}" + "=" * 65 + COLOR_RESET)

def print_banner() -> None:
    """Prints the bot ASCII art banner."""
    print(ASCII_BANNER)

def display_balance(service: OrderService) -> None:
    """Fetches and renders account balance and margin details in a clean table."""
    try:
        print(f"{COLOR_YELLOW}{get_info_symbol()} Fetching account balances from Binance Testnet...{COLOR_RESET}")
        balances = service.get_account_balances()
        
        print_header("💰 ACCOUNT BALANCES & MARGIN SUMMARY", COLOR_CYAN)
        print(f"  {COLOR_BOLD}{'ASSET':<10} {'BALANCE':<16} {'AVAILABLE':<16} {'UNREALIZED PNL':<15}{COLOR_RESET}")
        print(f"  {'-'*60}")
        
        found = False
        for b in balances:
            bal = float(b.get("balance", 0.0))
            avail = float(b.get("availableBalance", 0.0))
            pnl = float(b.get("crossUnPnl", 0.0))
            asset = b.get("asset", "")
            
            if bal > 0 or avail > 0 or asset == "USDT":
                found = True
                pnl_str = f"{COLOR_GREEN}+{pnl:.4f}{COLOR_RESET}" if pnl >= 0 else f"{COLOR_RED}{pnl:.4f}{COLOR_RESET}"
                print(f"  {asset:<10} {bal:<16.4f} {avail:<16.4f} {pnl_str}")
        
        if not found:
            print("  (No non-zero balances found)")
            
        print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)
    except Exception as e:
        print(f"{COLOR_RED}{get_failure_symbol()} Failed to retrieve account balance: {e}{COLOR_RESET}")

def display_open_orders(service: OrderService, symbol: Optional[str] = None) -> None:
    """Fetches and displays active open orders."""
    try:
        print(f"{COLOR_YELLOW}{get_info_symbol()} Fetching active open orders from Binance Testnet...{COLOR_RESET}")
        orders = service.get_open_orders(symbol=symbol)
        
        title = f"📋 ACTIVE OPEN ORDERS ({symbol.upper() if symbol else 'ALL SYMBOLS'})"
        print_header(title, COLOR_CYAN)
        
        if not orders:
            print(f"  {COLOR_GREEN}✓ No open orders found.{COLOR_RESET}")
            print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)
            return

        print(f"  {COLOR_BOLD}{'ORDER ID':<14} {'SYMBOL':<10} {'SIDE':<6} {'TYPE':<12} {'PRICE':<12} {'QTY':<10}{COLOR_RESET}")
        print(f"  {'-'*62}")
        
        for o in orders:
            oid = o.get("orderId", "N/A")
            sym = o.get("symbol", "N/A")
            side = o.get("side", "N/A")
            side_colored = f"{COLOR_GREEN}{side:<6}{COLOR_RESET}" if side == "BUY" else f"{COLOR_RED}{side:<6}{COLOR_RESET}"
            otype = o.get("type", "N/A")
            price = format_price(o.get("price", 0.0))
            qty = o.get("origQty", "0")
            print(f"  {str(oid):<14} {sym:<10} {side_colored} {otype:<12} {price:<12} {qty:<10}")
            
        print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)
    except Exception as e:
        print(f"{COLOR_RED}{get_failure_symbol()} Failed to retrieve open orders: {e}{COLOR_RESET}")

def cancel_order_action(service: OrderService, symbol: str, order_id: str) -> None:
    """Cancels a specific order."""
    try:
        print(f"{COLOR_YELLOW}{get_info_symbol()} Requesting order cancellation on exchange...{COLOR_RESET}")
        res = service.cancel_order(symbol=symbol, order_id=order_id)
        print_header("✓ ORDER CANCELLED SUCCESSFULLY", COLOR_GREEN)
        print(f"  {COLOR_BOLD}Order ID:{COLOR_RESET} {res.get('orderId')}")
        print(f"  {COLOR_BOLD}Symbol:{COLOR_RESET}   {res.get('symbol')}")
        print(f"  {COLOR_BOLD}Status:{COLOR_RESET}   {res.get('status')}")
        print(f"{COLOR_GREEN}" + "=" * 65 + COLOR_RESET)
    except Exception as e:
        print(f"{COLOR_RED}{get_failure_symbol()} Failed to cancel order: {e}{COLOR_RESET}")

def display_logs(lines: int = 20) -> None:
    """Displays the most recent log entries from trading_bot.log."""
    log_file = "trading_bot.log"
    print_header("📄 RECENT EXECUTION LOGS", COLOR_CYAN)
    if not os.path.exists(log_file):
        print("  No log file found yet.")
        print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)
        return

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) >= lines else all_lines
            for line in recent:
                line_str = line.strip()
                if "ERROR" in line_str or "CRITICAL" in line_str:
                    print(f"  {COLOR_RED}{line_str}{COLOR_RESET}")
                elif "WARNING" in line_str:
                    print(f"  {COLOR_YELLOW}{line_str}{COLOR_RESET}")
                elif "INFO" in line_str:
                    print(f"  {COLOR_GREEN}{line_str}{COLOR_RESET}")
                else:
                    print(f"  {line_str}")
        print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)
    except Exception as e:
        print(f"{COLOR_RED}Failed to read log file: {e}{COLOR_RESET}")

def interactive_order_wizard(service: OrderService, logger: logging.Logger) -> None:
    """Step-by-step interactive prompt wizard to configure and submit an order."""
    print_header("🚀 INTERACTIVE ORDER CREATION WIZARD", COLOR_MAGENTA)
    
    # 1. Symbol
    sym_input = input(f"{COLOR_BOLD}Enter Symbol (e.g. BTCUSDT, ETHUSDT) [default BTCUSDT]: {COLOR_RESET}").strip().upper()
    symbol = sym_input if sym_input else "BTCUSDT"
    
    # 2. Side
    print(f"\n{COLOR_BOLD}Select Order Side:{COLOR_RESET}")
    print("  [1] BUY (Long)")
    print("  [2] SELL (Short)")
    side_choice = input(f"{COLOR_BOLD}Choice (1 or 2) [default 1]: {COLOR_RESET}").strip()
    side = "SELL" if side_choice == "2" else "BUY"
    
    # 3. Order Type
    print(f"\n{COLOR_BOLD}Select Order Type:{COLOR_RESET}")
    print("  [1] MARKET")
    print("  [2] LIMIT")
    print("  [3] STOP_MARKET")
    type_choice = input(f"{COLOR_BOLD}Choice (1, 2, or 3) [default 1]: {COLOR_RESET}").strip()
    if type_choice == "2":
        order_type = "LIMIT"
    elif type_choice == "3":
        order_type = "STOP_MARKET"
    else:
        order_type = "MARKET"
        
    # 4. Quantity
    qty_str = input(f"\n{COLOR_BOLD}Enter Order Quantity (e.g. 0.002 for BTC, 0.05 for ETH): {COLOR_RESET}").strip()
    try:
        quantity = float(qty_str)
    except ValueError:
        print(f"{COLOR_RED}Invalid quantity numeric value. Aborting wizard.{COLOR_RESET}")
        return

    # 5. Price (if LIMIT)
    price = None
    if order_type == "LIMIT":
        price_str = input(f"{COLOR_BOLD}Enter Limit Price in USDT (e.g. 65000.00): {COLOR_RESET}").strip()
        try:
            price = float(price_str)
        except ValueError:
            print(f"{COLOR_RED}Invalid price numeric value. Aborting wizard.{COLOR_RESET}")
            return

    # 6. Stop Price (if STOP_MARKET)
    stop_price = None
    if order_type == "STOP_MARKET":
        stop_str = input(f"{COLOR_BOLD}Enter Stop Price in USDT (e.g. 64000.00): {COLOR_RESET}").strip()
        try:
            stop_price = float(stop_str)
        except ValueError:
            print(f"{COLOR_RED}Invalid stop price numeric value. Aborting wizard.{COLOR_RESET}")
            return

    # Order Review Card
    print("\n")
    print_header("ORDER REVIEW & CONFIRMATION", COLOR_CYAN)
    print(f"  {COLOR_BOLD}Symbol:{COLOR_RESET}      {symbol}")
    print(f"  {COLOR_BOLD}Side:{COLOR_RESET}        {side}")
    print(f"  {COLOR_BOLD}Order Type:{COLOR_RESET}  {order_type}")
    print(f"  {COLOR_BOLD}Quantity:{COLOR_RESET}    {quantity}")
    if price is not None:
        print(f"  {COLOR_BOLD}Limit Price:{COLOR_RESET} {price} USDT")
    if stop_price is not None:
        print(f"  {COLOR_BOLD}Stop Price:{COLOR_RESET}  {stop_price} USDT")
    print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)

    confirm = input(f"{COLOR_BOLD}Submit this order to Binance Testnet now? (y/n) [default y]: {COLOR_RESET}").strip().lower()
    if confirm and confirm != "y" and confirm != "yes":
        print(f"{COLOR_YELLOW}Order creation cancelled by user.{COLOR_RESET}")
        return

    # Execute
    print(f"\n{COLOR_YELLOW}{get_info_symbol()} Dispatching order payload to exchange...{COLOR_RESET}")
    try:
        execution = service.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
        
        print_header(f"{get_success_symbol()} ORDER PLACED SUCCESSFULLY", COLOR_GREEN)
        print(f"  {COLOR_BOLD}Order ID:{COLOR_RESET}      {execution['orderId']}")
        print(f"  {COLOR_BOLD}Status:{COLOR_RESET}        {execution['status']}")
        print(f"  {COLOR_BOLD}Executed Qty:{COLOR_RESET}  {execution['executedQty']} (of {execution['origQty']})")
        print(f"  {COLOR_BOLD}Average Price:{COLOR_RESET} {format_price(execution['avgPrice'])} USDT")
        print(f"  {COLOR_BOLD}Symbol/Side:{COLOR_RESET}   {execution['symbol']} / {execution['side']}")
        print(f"  {COLOR_BOLD}Type/ClientID:{COLOR_RESET} {execution['type']} / {execution['clientOrderId']}")
        print(f"{COLOR_GREEN}" + "=" * 65 + COLOR_RESET)
    except Exception as e:
        print_header(f"{get_failure_symbol()} ORDER PLACEMENT FAILED", COLOR_RED)
        print(f"  {COLOR_BOLD}Error:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 65 + COLOR_RESET)

def run_interactive_menu(logger: logging.Logger) -> None:
    """Runs the main interactive terminal menu loop."""
    print_banner()
    verify_config()
    client = BinanceClient()
    service = OrderService(client=client)

    while True:
        print(f"\n{COLOR_CYAN}{COLOR_BOLD}MAIN MENU - CHOOSE AN ACTION:{COLOR_RESET}")
        print(f"  [1] 🚀 Place New Order (Interactive Wizard)")
        print(f"  [2] 💰 View Account Balance & Available Margin")
        print(f"  [3] 📋 View Active Open Orders")
        print(f"  [4] ❌ Cancel an Active Open Order")
        print(f"  [5] 📄 View Recent Execution Logs")
        print(f"  [6] 🚪 Exit")
        
        choice = input(f"\n{COLOR_BOLD}Enter choice (1-6): {COLOR_RESET}").strip()
        
        if choice == "1":
            interactive_order_wizard(service, logger)
        elif choice == "2":
            display_balance(service)
        elif choice == "3":
            sym = input(f"{COLOR_BOLD}Filter by symbol (leave blank for all): {COLOR_RESET}").strip()
            display_open_orders(service, symbol=sym if sym else None)
        elif choice == "4":
            sym = input(f"{COLOR_BOLD}Enter Symbol (e.g. BTCUSDT, ETHUSDT): {COLOR_RESET}").strip().upper()
            oid = input(f"{COLOR_BOLD}Enter Order ID to cancel: {COLOR_RESET}").strip()
            if sym and oid:
                cancel_order_action(service, symbol=sym, order_id=oid)
            else:
                print(f"{COLOR_RED}Symbol and Order ID are required.{COLOR_RESET}")
        elif choice == "5":
            display_logs(lines=25)
        elif choice == "6" or choice.lower() in ["exit", "q", "quit"]:
            print(f"\n{COLOR_GREEN}Exiting Trading Bot CLI. Goodbye!{COLOR_RESET}\n")
            break
        else:
            print(f"{COLOR_RED}Invalid option '{choice}'. Please enter a number between 1 and 6.{COLOR_RESET}")

def main(args_list: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point function. Handles direct command-line arguments as well as interactive mode.
    """
    logger = setup_logging("trading_bot.log")
    logger.info("Application starting...")

    # Check if executed with no arguments (e.g. `python main.py`), launch interactive menu automatically
    if args_list is None and len(sys.argv) == 1:
        try:
            run_interactive_menu(logger)
            return 0
        except KeyboardInterrupt:
            print(f"\n{COLOR_YELLOW}\nUser interrupted. Exiting trading bot...{COLOR_RESET}")
            return 0
        except Exception as e:
            print(f"{COLOR_RED}Interactive session error: {e}{COLOR_RESET}")
            return 1

    parser = argparse.ArgumentParser(
        description="Production-grade Binance Futures Testnet (USDT-M) Trading CLI Bot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch the interactive terminal wizard menu"
    )
    parser.add_argument(
        "-b", "--balance",
        action="store_true",
        help="Fetch and display Binance Futures account balances and available margin"
    )
    parser.add_argument(
        "-o", "--open-orders",
        action="store_true",
        help="Fetch and display currently open active orders"
    )
    parser.add_argument(
        "--cancel-order",
        type=str,
        default=None,
        help="Order ID to cancel (must also specify --symbol)"
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="Display recent execution logs from trading_bot.log"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Trading pair symbol (e.g., BTCUSDT, ETHUSDT)"
    )
    parser.add_argument(
        "--side",
        type=str,
        default=None,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order execution side (BUY or SELL)"
    )
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"],
        help="Order execution type (MARKET, LIMIT, or STOP_MARKET)"
    )
    parser.add_argument(
        "--quantity",
        type=float,
        default=None,
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

    parsed = parser.parse_args(args_list)

    # 1. Handle Interactive flag
    if parsed.interactive:
        try:
            run_interactive_menu(logger)
            return 0
        except KeyboardInterrupt:
            print(f"\n{COLOR_YELLOW}\nUser interrupted. Exiting trading bot...{COLOR_RESET}")
            return 0

    # 2. Handle Logs flag
    if parsed.logs:
        display_logs()
        return 0

    # Initialize client/service for other single commands
    try:
        verify_config()
        client = BinanceClient()
        service = OrderService(client=client)

        # 3. Handle Balance flag
        if parsed.balance:
            display_balance(service)
            return 0

        # 4. Handle Open Orders flag
        if parsed.open_orders:
            display_open_orders(service, symbol=parsed.symbol)
            return 0

        # 5. Handle Cancel Order flag
        if parsed.cancel_order:
            if not parsed.symbol:
                print(f"{COLOR_RED}Error: --symbol is required when using --cancel-order.{COLOR_RESET}")
                return 1
            cancel_order_action(service, symbol=parsed.symbol, order_id=parsed.cancel_order)
            return 0

        # 6. Standard Order Placement Execution
        if not parsed.symbol or not parsed.side or not parsed.type or parsed.quantity is None:
            print_banner()
            print(f"{COLOR_YELLOW}No specific action specified. Launching Interactive Menu...{COLOR_RESET}\n")
            run_interactive_menu(logger)
            return 0

        raw_symbol = parsed.symbol
        raw_side = parsed.side.upper()
        raw_type = parsed.type.upper()
        raw_qty = parsed.quantity
        raw_price = parsed.price
        raw_stop_price = parsed.stop_price

        print_header("ORDER REQUEST SUMMARY", COLOR_CYAN)
        print(f"  {COLOR_BOLD}Symbol:{COLOR_RESET}      {raw_symbol.upper()}")
        print(f"  {COLOR_BOLD}Side:{COLOR_RESET}        {raw_side}")
        print(f"  {COLOR_BOLD}Order Type:{COLOR_RESET}  {raw_type}")
        print(f"  {COLOR_BOLD}Quantity:{COLOR_RESET}    {raw_qty}")
        if raw_price is not None:
            print(f"  {COLOR_BOLD}Limit Price:{COLOR_RESET} {format_price(raw_price)} USDT")
        if raw_stop_price is not None:
            print(f"  {COLOR_BOLD}Stop Price:{COLOR_RESET}  {format_price(raw_stop_price)} USDT")
        print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)
        print(f"{COLOR_YELLOW}{get_info_symbol()} Validating execution parameters locally...{COLOR_RESET}")

        validated = validate_order_inputs(
            symbol=raw_symbol,
            side=raw_side,
            order_type=raw_type,
            quantity=raw_qty,
            price=raw_price,
            stop_price=raw_stop_price
        )
        
        symbol_v, side_v, type_v, qty_v, price_v, stop_price_v = validated
        logger.info(f"Pre-flight parameters passed: {side_v} {type_v} for {qty_v} contracts of {symbol_v}")

        print(f"{COLOR_YELLOW}{get_info_symbol()} Connecting to Binance Futures Testnet...{COLOR_RESET}")
        print(f"{COLOR_YELLOW}{get_info_symbol()} Dispatching order payload to exchange...{COLOR_RESET}")
        execution = service.place_order(
            symbol=symbol_v,
            side=side_v,
            order_type=type_v,
            quantity=qty_v,
            price=price_v,
            stop_price=stop_price_v
        )

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
        
        print(f"{COLOR_GREEN}" + "=" * 65 + COLOR_RESET)
        print(f"{COLOR_GREEN}💡 Success details recorded in trading_bot.log{COLOR_RESET}")
        logger.info(f"CLI successful execution completed for order ID: {execution['orderId']}")
        return 0

    except ValidationError as e:
        logger.warning(f"Local Pre-flight validation rejected parameters: {e}")
        header_text = f"{get_failure_symbol()} LOCAL VALIDATION ERROR"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}Reason:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 65 + COLOR_RESET)
        return 1

    except ConfigurationError as e:
        logger.error(f"Environment configuration mismatch: {e}")
        header_text = f"{get_failure_symbol()} CONFIGURATION ERROR"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}Reason:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 65 + COLOR_RESET)
        return 1

    except ExchangeConnectionError as e:
        logger.error(f"Network connectivity failure: {e}")
        header_text = f"{get_failure_symbol()} NETWORK CONNECTION FAILURE"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}Reason:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 65 + COLOR_RESET)
        return 1

    except ExchangeAPIError as e:
        logger.error(f"Exchange refused request: {e}")
        header_text = f"{get_failure_symbol()} EXCHANGE API REFUSED REQUEST"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}HTTP Code:{COLOR_RESET} {e.status_code}")
        print(f"  {COLOR_BOLD}Error Code:{COLOR_RESET} {e.binance_code}")
        print(f"  {COLOR_BOLD}Message:{COLOR_RESET} {e.args[0]}")
        print(f"{COLOR_RED}" + "=" * 65 + COLOR_RESET)
        return 1

    except Exception as e:
        logger.critical(f"Unhandled general exception occurred: {e}", exc_info=True)
        header_text = f"{get_failure_symbol()} CRITICAL BOT EXCEPTION"
        print_header(header_text, COLOR_RED)
        print(f"  {COLOR_BOLD}An unexpected system error occurred:{COLOR_RESET} {e}")
        print(f"{COLOR_RED}" + "=" * 65 + COLOR_RESET)
        return 1

if __name__ == "__main__":
    sys.exit(main())
