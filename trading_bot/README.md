# Binance Futures (USDT-M) REST-API CLI Trading Bot
### PrimeTrade.ai hiring assignment — Senior Quantitative Software Engineer

A complete, production-grade, and highly robust command-line trading application for placing orders on the **Binance Futures Testnet (USDT-M)**. Built entirely in modern, PEP-8 compliant Python 3.10+, utilizing direct HTTP REST API integrations (cryptographic HMAC-SHA256 signing, server-client time synchronization, clock-drift offset handling, secure credential obfuscation logging, and parameter validations).

---

## 🏗️ Project Structure

```text
trading_bot/
│
├── bot/
│   ├── __init__.py         # Package entry & config verification
│   ├── client.py           # Custom REST client, clock-drift sync, cryptographic signature
│   ├── orders.py           # Order service layer compiling MARKET, LIMIT & STOP_MARKET payloads
│   ├── validators.py       # Pre-flight business parameter checkers (type/range/dependencies)
│   ├── logging_config.py   # Dual-handler secure obfuscating logging setup (disk + stdout)
│   ├── exceptions.py       # Domain-specific custom trading errors (ExchangeAPIError, etc.)
│   ├── utils.py            # Price/timestamp formatting & key masking utilities
│   └── cli.py              # Main CLI shell, argparse inputs, and formatted console UI
│
├── tests/
│   ├── __init__.py
│   └── test_bot.py         # Complete 16-test unittest suite for validators & payloads
│
├── .env.template           # Template environment setup
├── README.md               # Quickstart & user documentation
└── requirements.txt        # Minimal production dependencies
```

---

## ⚡ Technical Features

1. **Cryptographic Signing Layer**: Custom REST layer. Generates HMAC-SHA256 hashes using the secret key over parameter query strings, appending exact signatures and timestamps.
2. **Server Time Synchronization**: Connects to `GET /fapi/v1/time` on startup to calculate clock drift latency. Offsets system times automatically to bypass Binance's strict `recvWindow` check.
3. **Dual-Handler Obfuscating Logger**:
   - Detailed, high-verbosity traces (`DEBUG` and above) are logged to `/trading_bot.log`.
   - Clean, high-level info (`INFO` and above) is printed to stdout.
   - **Secret Protection Filter**: Raw API secrets are replaced with `[REDACTED_SECRET]` and API keys are masked to `ABCD********XYZ` before being committed to disk or console.
4. **Pre-flight Parameter Validation**: Inputs are sanitized and type-coerced. Throws explicit local `ValidationError` exceptions before invoking network IO.
5. **Robust Error Mapping**: Translates raw exchange HTTP codes into context-aware domain-specific exceptions.

---

## 🔑 Fetching Binance Testnet API Keys

1. Navigate to the [Binance Futures Testnet Registry](https://testnet.binancefuture.com).
2. Deposit mock USD assets in your wallet faucet.
3. Generate your **API Key** and **Secret Key**.

---

## 🚀 Installation & Command-Line Usage

```bash
# 1. Enter directory
cd trading_bot

# 2. Activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials in .env
BINANCE_API_KEY="your_actual_binance_testnet_api_key"
BINANCE_API_SECRET="your_actual_binance_testnet_secret_key"
```

### Command Execution Examples

```bash
# Market Order
python3 bot/cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002

# Limit Order
python3 bot/cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 1.5 --price 3450.75

# Stop Market Order
python3 bot/cli.py --symbol SOLUSDT --side BUY --type STOP_MARKET --quantity 10.0 --stop-price 155.50
```

---

## 🧪 Unit Tests

```bash
python3 -m unittest discover -s tests
```
