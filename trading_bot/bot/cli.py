"""
Command-Line Interface (CLI) Entry Point.

Builds the CLI parser, supports both direct flag execution, short positional commands
(e.g., `python main.py buy BTCUSDT 0.002`), command-line API key flags (-k / -s),
and an interactive terminal menu/wizard.
"""

import argparse
import logging
import os
import sys
import traceback
from typing import List, Optional

from bot.config import config, ConfigurationError
from bot import verify_config
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

def reconfigure_keys() -> None:
    """Interactively re-configures Binance API Key and Secret."""
    print_header("🔑 UPDATE BINANCE API CREDENTIALS", COLOR_YELLOW)
    new_key = input(f"{COLOR_BOLD}Enter Binance Testnet API Key: {COLOR_RESET}").strip()
    new_secret = input(f"{COLOR_BOLD}Enter Binance Testnet API Secret: {COLOR_RESET}").strip()
    if new_key and new_secret:
        config.set_credentials(new_key, new_secret)
        save_env = input(f"{COLOR_CYAN}Save credentials to .env file? (y/n) [default y]: {COLOR_RESET}").strip().lower()
        if save_env in ("", "y", "yes"):
            try:
                env_content = f"BINANCE_API_KEY={new_key}\nBINANCE_API_SECRET={new_secret}\nTESTNET_URL=https://testnet.binancefuture.com\n"
                with open(".env", "w", encoding="utf-8") as f:
                    f.write(env_content)
                with open(os.path.join("trading_bot", ".env"), "w", encoding="utf-8") as f:
                    f.write(env_content)
                print(f"{COLOR_GREEN}✓ API Credentials saved to .env!{COLOR_RESET}\n")
            except Exception as e:
                print(f"{COLOR_RED}Could not write to .env: {e}{COLOR_RESET}\n")
    else:
        print(f"{COLOR_RED}API Key and Secret cannot be empty.{COLOR_RESET}")

def run_interactive_menu(logger: logging.Logger) -> None:
    """Runs the main interactive terminal menu loop and command shell."""
    print_banner()
    
    # Ensure API Key and Secret are collected if missing
    try:
        config.verify(interactive_prompt=True)
    except ConfigurationError as e:
        print(f"{COLOR_RED}{e}{COLOR_RESET}")
        return

    client = BinanceClient()
    service = OrderService(client=client)

    print(f"\n{COLOR_GREEN}✓ Connected to Binance Testnet successfully!{COLOR_RESET}")
    print(f"{COLOR_CYAN}Type menu numbers (1-6) or type commands directly (e.g. 'buy BTCUSDT 0.002', 'balance', 'orders', 'keys', 'help', 'exit').{COLOR_RESET}")

    while True:
        print(f"\n{COLOR_CYAN}{COLOR_BOLD}COMMANDS & MENU OPTIONS:{COLOR_RESET}")
        print(f"  [1] 🚀 Interactive Order Wizard")
        print(f"  [2] 💰 Balance (`balance`)")
        print(f"  [3] 📋 Open Orders (`orders`)")
        print(f"  [4] ❌ Cancel Order (`cancel <SYMBOL> <ID>`)")
        print(f"  [5] 📄 View Logs (`logs`)")
        print(f"  [k] 🔑 Update API Keys (`keys`)")
        print(f"  [6] 🚪 Exit (`exit`)")
        
        user_input = input(f"\n{COLOR_BOLD}{COLOR_MAGENTA}trading-bot> {COLOR_RESET}").strip()
        if not user_input:
            continue

        parts = user_input.split()
        cmd = parts[0].lower()

        if user_input == "1":
            interactive_order_wizard(service, logger)
        elif user_input == "2" or cmd in ("balance", "bal"):
            display_balance(service)
        elif user_input == "3" or cmd in ("orders", "open"):
            sym = parts[1].upper() if len(parts) > 1 else None
            if not sym and user_input == "3":
                sym_in = input(f"{COLOR_BOLD}Filter by symbol (leave blank for all): {COLOR_RESET}").strip()
                sym = sym_in.upper() if sym_in else None
            display_open_orders(service, symbol=sym)
        elif user_input == "4" or cmd == "cancel":
            if len(parts) >= 3:
                cancel_order_action(service, symbol=parts[1].upper(), order_id=parts[2])
            else:
                sym = input(f"{COLOR_BOLD}Enter Symbol (e.g. BTCUSDT): {COLOR_RESET}").strip().upper()
                oid = input(f"{COLOR_BOLD}Enter Order ID to cancel: {COLOR_RESET}").strip()
                if sym and oid:
                    cancel_order_action(service, symbol=sym, order_id=oid)
                else:
                    print(f"{COLOR_RED}Symbol and Order ID are required.{COLOR_RESET}")
        elif user_input == "5" or cmd in ("logs", "log"):
            display_logs(lines=25)
        elif cmd in ("k", "keys", "config", "key"):
            reconfigure_keys()
            # Re-initialize client & service with new keys
            client = BinanceClient()
            service = OrderService(client=client)
        elif user_input == "6" or cmd in ("exit", "q", "quit"):
            print(f"\n{COLOR_GREEN}Exiting Trading Bot CLI. Goodbye!{COLOR_RESET}\n")
            break
        elif cmd in ("help", "h", "?"):
            print_header("📖 CLI COMMAND HELP", COLOR_CYAN)
            print("  buy <SYMBOL> <QTY> [PRICE]     e.g., buy BTCUSDT 0.002")
            print("                                 e.g., buy BTCUSDT 0.002 65000")
            print("  sell <SYMBOL> <QTY> [PRICE]    e.g., sell ETHUSDT 0.05 3500")
            print("  balance                        View balances & available margin")
            print("  orders [SYMBOL]                View open active orders")
            print("  cancel <SYMBOL> <ORDER_ID>     Cancel specific open order")
            print("  logs                           View execution log history")
            print("  keys                           Re-enter / update Binance API Key & Secret")
            print("  exit                           Close CLI session")
            print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)
        elif cmd in ("buy", "sell"):
            side = cmd.upper()
            if len(parts) >= 3:
                symbol = parts[1].upper()
                try:
                    qty = float(parts[2])
                except ValueError:
                    print(f"{COLOR_RED}Invalid quantity numeric value: {parts[2]}{COLOR_RESET}")
                    continue
                
                price = None
                order_type = "MARKET"
                if len(parts) >= 4:
                    try:
                        price = float(parts[3])
                        order_type = "LIMIT"
                    except ValueError:
                        print(f"{COLOR_RED}Invalid price numeric value: {parts[3]}{COLOR_RESET}")
                        continue

                try:
                    validated = validate_order_inputs(
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        quantity=qty,
                        price=price
                    )
                    sym_v, side_v, type_v, qty_v, price_v, _ = validated

                    print(f"{COLOR_YELLOW}{get_info_symbol()} Dispatching order payload to exchange...{COLOR_RESET}")
                    execution = service.place_order(
                        symbol=sym_v,
                        side=side_v,
                        order_type=type_v,
                        quantity=qty_v,
                        price=price_v
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
                    print(f"{COLOR_RED}{get_failure_symbol()} Order placement failed: {e}{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}Usage: {cmd} <SYMBOL> <QUANTITY> [PRICE]{COLOR_RESET}")
                print(f"Example: {cmd} BTCUSDT 0.002")
                print(f"Example: {cmd} BTCUSDT 0.002 65000")
        else:
            print(f"{COLOR_RED}Unknown option or command '{user_input}'. Type 'help' or '1'-'6'.{COLOR_RESET}")

def main(args_list: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point function. Handles direct flags, short positional commands,
    API key arguments, and interactive menu wizard.
    """
    logger = setup_logging("trading_bot.log")
    logger.info("Application starting...")

    raw_args = list(args_list) if args_list is not None else sys.argv[1:]

    # Check for -k / --api-key and -s / --api-secret in arguments
    api_key_override = None
    api_secret_override = None

    filtered_args = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg in ("-k", "--api-key") and i + 1 < len(raw_args):
            api_key_override = raw_args[i + 1]
            i += 2
        elif arg in ("-s", "--api-secret") and i + 1 < len(raw_args):
            api_secret_override = raw_args[i + 1]
            i += 2
        else:
            filtered_args.append(arg)
            i += 1

    if api_key_override or api_secret_override:
        config.set_credentials(api_key_override or "", api_secret_override or "")

    # Check for short positional commands (e.g. `python main.py buy BTCUSDT 0.002 [price]`)
    positional_action = None
    pos_symbol = None
    pos_side = None
    pos_type = None
    pos_qty = None
    pos_price = None
    pos_order_id = None

    if filtered_args:
        cmd = filtered_args[0].lower()
        if cmd in ("buy", "sell"):
            pos_side = cmd.upper()
            if len(filtered_args) >= 3:
                pos_symbol = filtered_args[1].upper()
                try:
                    pos_qty = float(filtered_args[2])
                except ValueError:
                    print(f"{COLOR_RED}Error: Quantity '{filtered_args[2]}' must be a valid number.{COLOR_RESET}")
                    return 1

                if len(filtered_args) >= 4:
                    try:
                        pos_price = float(filtered_args[3])
                        pos_type = "LIMIT"
                    except ValueError:
                        print(f"{COLOR_RED}Error: Price '{filtered_args[3]}' must be a valid number.{COLOR_RESET}")
                        return 1
                else:
                    pos_type = "MARKET"
                positional_action = "place_order"
            else:
                print(f"{COLOR_RED}Usage: python main.py {cmd} <SYMBOL> <QUANTITY> [PRICE]{COLOR_RESET}")
                print(f"Example: python main.py {cmd} BTCUSDT 0.002")
                print(f"Example: python main.py {cmd} BTCUSDT 0.002 65000")
                return 1

        elif cmd in ("balance", "bal"):
            positional_action = "balance"
        elif cmd in ("orders", "open"):
            positional_action = "open_orders"
            if len(filtered_args) >= 2:
                pos_symbol = filtered_args[1].upper()
        elif cmd == "cancel":
            if len(filtered_args) >= 3:
                pos_symbol = filtered_args[1].upper()
                pos_order_id = filtered_args[2]
                positional_action = "cancel_order"
            else:
                print(f"{COLOR_RED}Usage: python main.py cancel <SYMBOL> <ORDER_ID>{COLOR_RESET}")
                return 1
        elif cmd in ("logs", "log"):
            positional_action = "logs"
        elif cmd in ("menu", "wizard", "interactive", "-i", "--interactive"):
            positional_action = "interactive"

    # Handle direct positional shortcuts immediately
    if positional_action == "logs":
        display_logs()
        return 0

    if positional_action == "interactive" or (not filtered_args and positional_action is None):
        try:
            run_interactive_menu(logger)
            return 0
        except KeyboardInterrupt:
            print(f"\n{COLOR_YELLOW}\nUser interrupted. Exiting trading bot...{COLOR_RESET}")
            return 0

    # For actions requiring API calls, verify configuration (with interactive prompt fallback if needed)
    try:
        config.verify(interactive_prompt=True)
        client = BinanceClient()
        service = OrderService(client=client)

        if positional_action == "balance":
            display_balance(service)
            return 0

        if positional_action == "open_orders":
            display_open_orders(service, symbol=pos_symbol)
            return 0

        if positional_action == "cancel_order":
            cancel_order_action(service, symbol=pos_symbol, order_id=pos_order_id)
            return 0

        if positional_action == "place_order":
            print_header("ORDER REQUEST SUMMARY", COLOR_CYAN)
            print(f"  {COLOR_BOLD}Symbol:{COLOR_RESET}      {pos_symbol}")
            print(f"  {COLOR_BOLD}Side:{COLOR_RESET}        {pos_side}")
            print(f"  {COLOR_BOLD}Order Type:{COLOR_RESET}  {pos_type}")
            print(f"  {COLOR_BOLD}Quantity:{COLOR_RESET}    {pos_qty}")
            if pos_price is not None:
                print(f"  {COLOR_BOLD}Limit Price:{COLOR_RESET} {format_price(pos_price)} USDT")
            print(f"{COLOR_CYAN}" + "=" * 65 + COLOR_RESET)

            validated = validate_order_inputs(
                symbol=pos_symbol,
                side=pos_side,
                order_type=pos_type,
                quantity=pos_qty,
                price=pos_price
            )
            symbol_v, side_v, type_v, qty_v, price_v, _ = validated

            print(f"{COLOR_YELLOW}{get_info_symbol()} Dispatching order payload to exchange...{COLOR_RESET}")
            execution = service.place_order(
                symbol=symbol_v,
                side=side_v,
                order_type=type_v,
                quantity=qty_v,
                price=price_v
            )

            header_text = f"{get_success_symbol()} ORDER PLACED SUCCESSFULLY"
            print_header(header_text, COLOR_GREEN)
            print(f"  {COLOR_BOLD}Order ID:{COLOR_RESET}      {execution['orderId']}")
            print(f"  {COLOR_BOLD}Status:{COLOR_RESET}        {execution['status']}")
            print(f"  {COLOR_BOLD}Executed Qty:{COLOR_RESET}  {execution['executedQty']} (of {execution['origQty']})")
            print(f"  {COLOR_BOLD}Average Price:{COLOR_RESET} {format_price(execution['avgPrice'])} USDT")
            print(f"  {COLOR_BOLD}Symbol/Side:{COLOR_RESET}   {execution['symbol']} / {execution['side']}")
            print(f"  {COLOR_BOLD}Type/ClientID:{COLOR_RESET} {execution['type']} / {execution['clientOrderId']}")
            print(f"{COLOR_GREEN}" + "=" * 65 + COLOR_RESET)
            return 0

    except (ValidationError, ConfigurationError, ExchangeConnectionError, ExchangeAPIError) as e:
        print(f"{COLOR_RED}{get_failure_symbol()} Error: {e}{COLOR_RESET}")
        return 1

    # Fallback to standard ArgParse parser for legacy full flags
    parser = argparse.ArgumentParser(
        description="Production-grade Binance Futures Testnet (USDT-M) Trading CLI Bot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("-k", "--api-key", type=str, help="Binance Testnet API Key")
    parser.add_argument("-s", "--api-secret", type=str, help="Binance Testnet API Secret")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive wizard")
    parser.add_argument("-b", "--balance", action="store_true", help="Fetch account balances")
    parser.add_argument("-o", "--open-orders", action="store_true", help="Fetch open orders")
    parser.add_argument("--cancel-order", type=str, help="Order ID to cancel")
    parser.add_argument("--logs", action="store_true", help="Display recent execution logs")
    parser.add_argument("--symbol", type=str, help="Trading pair symbol (e.g., BTCUSDT)")
    parser.add_argument("--side", type=str, choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL")
    parser.add_argument("--type", type=str, choices=["MARKET", "LIMIT", "STOP_MARKET"], help="Order type")
    parser.add_argument("--quantity", type=float, help="Order quantity")
    parser.add_argument("--price", type=float, help="Limit price")
    parser.add_argument("--stop-price", type=float, help="Stop trigger price")

    parsed = parser.parse_args(filtered_args)

    if parsed.logs:
        display_logs()
        return 0

    try:
        config.verify(interactive_prompt=True)
        client = BinanceClient()
        service = OrderService(client=client)

        if parsed.balance:
            display_balance(service)
            return 0
        if parsed.open_orders:
            display_open_orders(service, symbol=parsed.symbol)
            return 0
        if parsed.cancel_order:
            if not parsed.symbol:
                print(f"{COLOR_RED}Error: --symbol required when cancelling order.{COLOR_RESET}")
                return 1
            cancel_order_action(service, symbol=parsed.symbol, order_id=parsed.cancel_order)
            return 0

        if not parsed.symbol or not parsed.side or not parsed.type or parsed.quantity is None:
            run_interactive_menu(logger)
            return 0

        raw_symbol = parsed.symbol
        raw_side = parsed.side.upper()
        raw_type = parsed.type.upper()
        raw_qty = parsed.quantity
        raw_price = parsed.price
        raw_stop_price = parsed.stop_price

        validated = validate_order_inputs(
            symbol=raw_symbol,
            side=raw_side,
            order_type=raw_type,
            quantity=raw_qty,
            price=raw_price,
            stop_price=raw_stop_price
        )
        symbol_v, side_v, type_v, qty_v, price_v, stop_price_v = validated

        execution = service.place_order(
            symbol=symbol_v,
            side=side_v,
            order_type=type_v,
            quantity=qty_v,
            price=price_v,
            stop_price=stop_price_v
        )

        print_header(f"{get_success_symbol()} ORDER PLACED SUCCESSFULLY", COLOR_GREEN)
        print(f"  {COLOR_BOLD}Order ID:{COLOR_RESET}      {execution['orderId']}")
        print(f"  {COLOR_BOLD}Status:{COLOR_RESET}        {execution['status']}")
        print(f"  {COLOR_BOLD}Executed Qty:{COLOR_RESET}  {execution['executedQty']} (of {execution['origQty']})")
        print(f"  {COLOR_BOLD}Average Price:{COLOR_RESET} {format_price(execution['avgPrice'])} USDT")
        print(f"  {COLOR_BOLD}Symbol/Side:{COLOR_RESET}   {execution['symbol']} / {execution['side']}")
        print(f"  {COLOR_BOLD}Type/ClientID:{COLOR_RESET} {execution['type']} / {execution['clientOrderId']}")
        print(f"{COLOR_GREEN}" + "=" * 65 + COLOR_RESET)
        return 0

    except Exception as e:
        print(f"{COLOR_RED}{get_failure_symbol()} Error: {e}{COLOR_RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
