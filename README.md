# Binance Futures (USDT-M) REST-API CLI Trading Bot
### PrimeTrade.ai hiring assignment — Senior Quantitative Software Engineer

A complete, production-grade, and highly robust command-line trading application for placing orders on the **Binance Futures Testnet (USDT-M)**. Built entirely in modern, PEP-8 compliant Python 3.10+, utilizing direct HTTP REST API integrations (cryptographic HMAC-SHA256 signing, server-client time synchronization, clock-drift offset handling, secure credential obfuscation logging, and parameter validations).

This repository also hosts a modern, full-stack **Vite + React + Express** web UI controller dashboard, enabling you to trigger CLI executions, inspect live terminal stdout/stderr, trace encrypted log histories, and run unit tests dynamically in real-time.

---

## 🏗️ Project Architecture & Layout

```text
trading_bot/
│
├── bot/
│   ├── __init__.py         # Package entry & config verification (placeholder prevention)
│   ├── client.py           # Custom REST client, clock-drift sync, cryptographic signature
│   ├── orders.py           # Order service layer compiling MARKET, LIMIT & STOP_MARKET payloads
│   ├── validators.py       # Pre-flight business parameter checkers (type/range/dependencies)
│   ├── logging_config.py   # Dual-handler secure obfuscating logging setup (disk + stdout)
│   ├── exceptions.py       # Domain-specific custom trading errors (ExchangeAPIError, etc.)
│   └── cli.py              # Main CLI shell, argparse inputs, and formatted console UI
│
├── tests/
│   ├── __init__.py
│   └── test_bot.py         # Complete unittest suite for validators & payload structures
│
├── .env.template           # Template environment setup
├── README.md               # Quickstart & user documentation (This file)
└── requirements.txt        # Minimal production dependencies (zero python-binance library)
```

---

## ⚡ Technical Features

1. **Cryptographic Signing Layer**: Custom REST layer. Generates HMAC-SHA256 hashes using the secret key over parameter query strings, appending exact signatures and timestamps.
2. **Server Time Synchronization**: Connects to `GET /fapi/v1/time` on startup to calculate clock drift latency. Offsets system times automatically to bypass Binance's strict `recvWindow` check.
3. **Dual-Handler Obfuscating Logger**:
   - Detailed, high-verbosity traces (`DEBUG` and above) are logged to `/trading_bot.log`. Format: `[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s`.
   - Clean, high-level info (`INFO` and above) is printed to the standard terminal output.
   - **Secret Protection Filter**: Logs are intercepted by a custom `ObfuscatingFormatter`. Raw API secrets are replaced with `[REDACTED_SECRET]` and API keys are masked to `ABCD********XYZ` before being committed to disk or console.
4. **Pre-flight Parameter Validation**: Inputs are fully sanitized and type-coerced. Throws explicit local `ValidationError` exceptions for empty symbols, invalid sides, negative sizes, or missing price dependencies before invoking network IO.
5. **Robust Error Mapping**: Translates raw exchange codes (e.g., `-2019` for margin issues, `-2015` for key issues) into context-aware domain-specific exceptions.

---

## 🔑 Fetching Binance Testnet API Keys

To run live mock trades on the Binance Futures Testnet, fetch your sandbox credentials:
1. Navigate to the [Binance Futures Testnet Registry](https://testnet.binancefuture.com) and register an account (supports Google, GitHub, or Email logins).
2. Deposit mock USD assets (click "Faucet" or request USDT test funds in your wallet).
3. Under the wallet section or top control panels, click **API Key** or **Generate API Key**.
4. Securely copy both the **API Key** and **Secret Key**.

---

## 🚀 Quickstart: Running on Laptop via Windows Command Prompt (CMD)

You do **NOT** need to create or edit any `.env` files manually! The application handles configuration automatically.

### Step 1: Open CMD and Clone the Repository
Open Command Prompt (`cmd.exe`) on your Windows laptop and run:
```cmd
git clone https://github.com/pandejesal/Binance-Futures-Trading-Bot.git
cd Binance-Futures-Trading-Bot
```

### Step 2: Create & Activate Python Virtual Environment
```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```cmd
pip install -r requirements.txt
```

### Step 4: Run the Bot
Simply execute:
```cmd
python main.py
```

> **🔑 Automated Credentials Setup:**
> On your first run, the bot will automatically detect if API credentials are missing and prompt you in CMD to enter your **Binance Testnet API Key** and **Secret Key**. It will then automatically save them for future runs!

---

## 💻 Usage Options & Command Cheat Sheet

### Option A: Interactive Command-Line Wizard (Recommended)
Run `python main.py` without arguments to launch the interactive menu:
```cmd
python main.py
```
This opens an interactive terminal menu with:
- 🚀 **Interactive Order Wizard**: Step-by-step prompts for Symbol, Side, Type, Quantity, Price, Stop Price with pre-flight review and confirmation.
- 💰 **View Account Balances**: Live USDT margin, wallet balances, and unrealized PnL.
- 📋 **View Active Open Orders**: Table of all live limit or stop orders on Binance Testnet.
- ❌ **Cancel Active Orders**: Quick selection to cancel open orders by Order ID.
- 📄 **View Execution Logs**: Inspect the latest entries in `trading_bot.log`.

---

### Option B: Quick Direct Short Commands
Run simple 2-4 word commands directly in Command Prompt (`cmd`):

```cmd
# 1. Check Account Margin & Wallet Balance
python main.py balance

# 2. Quick Market Buy (Symbol Quantity)
python main.py buy BTCUSDT 0.002

# 3. Quick Limit Buy (Symbol Quantity Price)
python main.py buy BTCUSDT 0.002 65000

# 4. Quick Market Sell (Symbol Quantity)
python main.py sell ETHUSDT 0.05

# 5. Quick Limit Sell (Symbol Quantity Price)
python main.py sell ETHUSDT 0.05 3500

# 6. Check Active Open Orders
python main.py orders

# 7. Cancel Open Order (Symbol OrderID)
python main.py cancel BTCUSDT 23202119036

# 8. View Live Execution Logs
python main.py logs
```

---

### Option C: Override Credentials via Command-Line Flags
If you prefer to pass your API credentials directly in CMD without saving them:
```cmd
python main.py -k YOUR_BINANCE_API_KEY -s YOUR_BINANCE_SECRET balance
python main.py -k YOUR_BINANCE_API_KEY -s YOUR_BINANCE_SECRET buy BTCUSDT 0.002
```

---

### Option D: Standard Command-Line Flags
```cmd
# Market Order
python main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002

# Limit Order
python main.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3500.00

# Stop Market Order
python main.py --symbol SOLUSDT --side BUY --type STOP_MARKET --quantity 10.0 --stop-price 155.50

# View Account Balances & Margin
python main.py --balance

# View Active Open Orders
python main.py --open-orders

# Cancel Active Order
python main.py --cancel-order 14098668081 --symbol ETHUSDT
```

---

## 🧪 Running Unit Tests

The test suite validates input parsing, exception definitions, and API specifications. Execute tests via python:

```bash
# From the trading_bot directory
python3 -m unittest discover -s tests
```

---

## 🛡️ Logging & Audit Traces

All outbound API request logs, timestamp signatures, cryptographic formulas, and exchange response payloads are recorded inside `/trading_bot.log`. 

An audit example from a successful MARKET order:
```text
[2026-07-21 08:12:15] [INFO] [client.py:64]: Clock synchronized. Offset: -14ms (latency: 18ms).
[2026-07-21 08:12:15] [INFO] [orders.py:63]: Pre-flight validation passed. Dispatching BUY MARKET order for 0.002 BTCUSDT...
[2026-07-21 08:12:15] [DEBUG] [client.py:120]: Sending Request: POST https://testnet.binancefuture.com/fapi/v1/order with params: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.002, 'timestamp': 1784621535014, 'recvWindow': 5000, 'signature': 'f7d2e8...masked_signature...'}
[2026-07-21 08:12:16] [DEBUG] [client.py:134]: Raw Response [HTTP 200]: {"orderId":284719273,"symbol":"BTCUSDT","status":"FILLED","clientOrderId":"x-A9C381","price":"0.00","avgPrice":"64050.25","origQty":"0.002","executedQty":"0.002","cumQty":"0.002","cumQuote":"128.1005","timeInForce":"GTC","type":"MARKET","side":"BUY", ...}
[2026-07-21 08:12:16] [INFO] [orders.py:120]: Successfully processed order! Order ID: 284719273 | Status: FILLED | Executed Qty: 0.002 | Avg Price: 64050.25
```
*(Notice how credentials like API Keys/Secrets are completely absent from debug parameter payloads).*
