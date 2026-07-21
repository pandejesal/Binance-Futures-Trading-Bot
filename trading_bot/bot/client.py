"""
Cryptographic Binance Futures Client Module.

Handles network interactions, server-client time synchronization, HMAC-SHA256 request signing,
header configuration, connection resiliency, and detailed request/response logging.
Supports both standard requests library and built-in urllib as a zero-dependency fallback.
"""

import hashlib
import hmac
import logging
import os
import time
import urllib.parse
import json
from typing import Any, Dict, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

from bot.exceptions import ExchangeAPIError, ExchangeConnectionError

class BinanceClient:
    """
    Direct REST API client for the Binance Futures Testnet (USDT-M).
    Performs server time synchronization and cryptographically signs requests with HMAC-SHA256.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> None:
        """
        Initializes the BinanceClient and synchronizes the local clock with the exchange.
        """
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://testnet.binancefuture.com"
        
        # Load keys from environment if not provided
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        
        self.time_offset = 0
        self.sync_server_time()

    def sync_server_time(self) -> None:
        """
        Fetches the current server time from the Binance Futures Testnet and
        calculates the offset relative to the local system clock. This prevents
        order rejection due to time drift.
        """
        url = f"{self.base_url}/fapi/v1/time"
        self.logger.debug(f"Fetching Binance server time from {url}...")
        
        try:
            start_time = time.time()
            if HAS_REQUESTS:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                server_time = response.json()["serverTime"]
            else:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=10) as res:
                    server_time = json.loads(res.read().decode("utf-8"))["serverTime"]
            end_time = time.time()
            
            # Simple latency adjustment (round-trip time division)
            latency = int((end_time - start_time) * 1000 / 2)
            local_time = int(time.time() * 1000)
            
            # Offset formula: server_time - (local_time + latency)
            self.time_offset = server_time - (local_time + latency)
            self.logger.info(
                f"Clock synchronized. Offset: {self.time_offset}ms (latency: {latency}ms)."
            )
        except Exception as e:
            self.logger.warning(
                f"Failed to synchronize server time: {e}. Defaulting to zero offset."
            )
            self.time_offset = 0

    def _sign_payload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Appends the synchronized timestamp, a safety recvWindow, and signs the parameters
        dictionary using HMAC-SHA256.
        """
        signed_params = params.copy()
        
        # Calculate synchronized timestamp
        synchronized_timestamp = int(time.time() * 1000) + self.time_offset
        signed_params["timestamp"] = synchronized_timestamp
        signed_params["recvWindow"] = 5000  # standard Binance safety window
        
        # Build query string
        query_string = urllib.parse.urlencode(signed_params)
        
        # Calculate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        signed_params["signature"] = signature
        return signed_params

    def send_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        authenticated: bool = True
    ) -> Dict[str, Any]:
        """
        Dispatches an HTTP request to the Binance Futures Testnet.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.).
            endpoint: URL path endpoint (e.g. /fapi/v1/order).
            params: Optional dictionary of query/payload parameters.
            authenticated: True if the request requires cryptographic signing and headers.

        Returns:
            The parsed JSON response dictionary.

        Raises:
            ExchangeConnectionError: For network issues, timeouts, or DNS failures.
            ExchangeAPIError: When the exchange returns a non-2xx response.
        """
        method = method.upper()
        request_params = params.copy() if params else {}

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "PrimeTradeAI-TradingBot/1.0"
        }

        if authenticated:
            if not self.api_key or not self.api_secret:
                raise ValueError("API credentials must be configured for authenticated requests.")
            headers["X-MBX-APIKEY"] = self.api_key
            # Sign parameters
            request_params = self._sign_payload(request_params)

        # Log detailed request parameters at the DEBUG level to the file handler.
        # Our custom ObfuscatingFormatter will automatically mask any credentials.
        self.logger.debug(
            f"Sending Request: {method} {self.base_url}{endpoint} with params: {request_params}"
        )

        try:
            if HAS_REQUESTS:
                url = f"{self.base_url}{endpoint}"
                if method == "GET":
                    response = requests.get(url, headers=headers, params=request_params, timeout=15)
                elif method == "POST":
                    response = requests.post(url, headers=headers, params=request_params, timeout=15)
                elif method == "DELETE":
                    response = requests.delete(url, headers=headers, params=request_params, timeout=15)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Log raw exchange response
                self.logger.debug(
                    f"Raw Response [HTTP {response.status_code}]: {response.text}"
                )

                # Handle non-success statuses
                if not (200 <= response.status_code < 300):
                    try:
                        err_json = response.json()
                        binance_msg = err_json.get("msg", "Unknown Binance error")
                        binance_code = err_json.get("code", -1)
                    except ValueError:
                        binance_msg = response.text
                        binance_code = -1
                    
                    raise ExchangeAPIError(
                        message=binance_msg,
                        status_code=response.status_code,
                        binance_code=binance_code
                    )

                return response.json()
            else:
                # Use standard library urllib fallback
                query_string = urllib.parse.urlencode(request_params)
                url = f"{self.base_url}{endpoint}"
                if query_string:
                    url = f"{url}?{query_string}"
                
                req = urllib.request.Request(url, headers=headers, method=method)
                try:
                    with urllib.request.urlopen(req, timeout=15) as res:
                        status_code = res.getcode()
                        response_text = res.read().decode("utf-8")
                        self.logger.debug(f"Raw Response [HTTP {status_code}]: {response_text}")
                        return json.loads(response_text)
                except urllib.error.HTTPError as e:
                    status_code = e.code
                    response_text = e.read().decode("utf-8")
                    self.logger.debug(f"Raw Response [HTTP {status_code}]: {response_text}")
                    try:
                        err_json = json.loads(response_text)
                        binance_msg = err_json.get("msg", "Unknown Binance error")
                        binance_code = err_json.get("code", -1)
                    except (ValueError, TypeError):
                        binance_msg = response_text
                        binance_code = -1
                    raise ExchangeAPIError(
                        message=binance_msg,
                        status_code=status_code,
                        binance_code=binance_code
                    )

        except ExchangeAPIError:
            raise
        except Exception as e:
            self.logger.error(f"Network error during {method} {endpoint}: {e}")
            raise ExchangeConnectionError(f"HTTP Request failed or timed out: {e}")
