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

## 🚀 Installation & Command-Line Usage

### 1. Prerequisites
- Python 3.10 or higher
- `pip` (Python Package Installer)

### 2. Setup environment
Create a virtual environment and install dependencies:

```bash
# Clone or enter the project directory
cd trading_bot

# Create a virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install minimalist dependencies (no python-binance wrapper needed)
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.template` into a new `.env` file:
```bash
cp .env.template .env
```
Open `.env` and fill in your keys:
```env
BINANCE_API_KEY="your_actual_binance_testnet_api_key"
BINANCE_API_SECRET="your_actual_binance_testnet_secret_key"
```

---

## 💻 CLI Command Execution & Interactive Wizard Examples

Run these commands from your terminal (make sure your virtualenv is activated and `.env` is loaded).

### A. Launch Interactive Terminal Menu / Wizard (Recommended)
Simply run `python main.py` with no flags (or with `-i` / `--interactive`) to open the interactive wizard:
```bash
python3 main.py
```
This opens an interactive menu offering:
- 🚀 **Interactive Order Wizard**: Step-by-step prompts for Symbol, Side, Type, Quantity, Price, Stop Price, with a pre-flight review card and execution confirmation.
- 💰 **View Account Balances**: Live USDT margin, wallet balances, and unrealized PnL.
- 📋 **View Active Open Orders**: Table of all live limit or stop orders on Binance Testnet.
- ❌ **Cancel Active Orders**: Quick selection to cancel open orders by Order ID.
- 📄 **View Execution Logs**: Inspect the latest entries in `trading_bot.log`.

---

### B. Direct Command-Line Flag Mode & Short Commands

#### ⚡ Ultra-Fast Short Commands (Recommended for Laptop / Command Prompt)
Run simple 2-4 word commands directly from your Windows Command Prompt (`cmd`), PowerShell, or terminal:

```bash
# 1. Quick Market Buy (Symbol Quantity)
python main.py buy BTCUSDT 0.002

# 2. Quick Limit Buy (Symbol Quantity Price)
python main.py buy BTCUSDT 0.002 65000

# 3. Quick Market Sell (Symbol Quantity)
python main.py sell ETHUSDT 0.05

# 4. Quick Limit Sell (Symbol Quantity Price)
python main.py sell ETHUSDT 0.05 3500

# 5. Quick Account Balance Check
python main.py balance

# 6. Quick Active Open Orders Check
python main.py orders

# 7. Quick Cancel Order (Symbol OrderID)
python main.py cancel BTCUSDT 23202119036

# 8. Quick View Execution Logs
python main.py logs

# 9. Pass API Key & Secret directly via flags (-k and -s)
python main.py -k YOUR_API_KEY -s YOUR_API_SECRET balance
```

> **Note on Automatic Credential Setup:** If `.env` is missing or keys are not set yet, running any command will automatically prompt you to paste your Binance Testnet API key and secret once, and offer to save them to `.env` automatically!

---

#### Standard Command-Line Flags
```bash
# Market Order
python3 main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002

# Limit Order
python3 main.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3500.00

# Stop Market Order
python3 main.py --symbol SOLUSDT --side BUY --type STOP_MARKET --quantity 10.0 --stop-price 155.50

# View Account Balances & Margin
python3 main.py --balance

# View Active Open Orders
python3 main.py --open-orders

# Cancel Active Order
python3 main.py --cancel-order 14098668081 --symbol ETHUSDT

# View Recent Execution Logs
python3 main.py --logs
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
