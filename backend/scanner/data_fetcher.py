"""
Fetches OHLCV candle data, funding rates, and open interest from exchanges via ccxt.
"""
import ccxt
import pandas as pd
import logging
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from backend.config import settings

logger = logging.getLogger(__name__)

_exchange: Optional[ccxt.Exchange] = None
_futures_exchange: Optional[ccxt.Exchange] = None


def get_exchange() -> ccxt.Exchange:
    """Get or create spot exchange instance."""
    global _exchange
    if _exchange is None:
        exchange_class = getattr(ccxt, settings.exchange_id)
        _exchange = exchange_class({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
    return _exchange


def get_futures_exchange() -> Optional[ccxt.Exchange]:
    """Get or create futures exchange instance for funding rate/OI data."""
    global _futures_exchange
    if _futures_exchange is None:
        try:
            exchange_class = getattr(ccxt, settings.exchange_id)
            _futures_exchange = exchange_class({
                "enableRateLimit": True,
                "options": {"defaultType": "swap"},
            })
        except Exception as e:
            logger.warning(f"Could not create futures exchange: {e}")
            return None
    return _futures_exchange


def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
    timeout: int = 30,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data for a symbol.

    Args:
        symbol: Trading pair symbol (e.g., "BTC/USDT")
        timeframe: Candle timeframe (e.g., "1d", "4h")
        limit: Number of candles to fetch
        timeout: Maximum time in seconds to wait for the API call (default: 30)

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
        Or None if fetch fails.
    """
    try:
        exchange = get_exchange()
        
        # Use ThreadPoolExecutor to add timeout to the blocking API call
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
            try:
                ohlcv = future.result(timeout=timeout)
            except FutureTimeoutError:
                logger.error(f"Timeout after {timeout}s while fetching {symbol} ({timeframe})")
                return None

        if not ohlcv:
            logger.warning(f"No data returned for {symbol} ({timeframe})")
            return None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)

        return df

    except Exception as e:
        logger.error(f"Error fetching {symbol} ({timeframe}): {e}")
        return None


def fetch_multi_timeframe(
    symbol: str,
    timeframes: List[str],
    limit: int = 200,
) -> Dict[str, Optional[pd.DataFrame]]:
    """Fetch OHLCV data across multiple timeframes."""
    result = {}
    for tf in timeframes:
        result[tf] = fetch_ohlcv(symbol, tf, limit)
    return result


def fetch_all_tickers(timeout: int = 60) -> Dict[str, dict]:
    """
    Fetch current ticker data for all pairs on the exchange.
    
    Args:
        timeout: Maximum time in seconds to wait for the API call (default: 60)
    
    Returns:
        Dictionary of ticker data, or empty dict if fetch fails or times out
    """
    try:
        exchange = get_exchange()
        
        # Use ThreadPoolExecutor to add timeout to the blocking API call
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(exchange.fetch_tickers)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError:
                logger.error(f"Timeout after {timeout}s while fetching all tickers")
                return {}
    except Exception as e:
        logger.error(f"Error fetching tickers: {e}")
        return {}


def get_top_coins_by_volume(n: int = 100, quote: str = "USDT") -> List[str]:
    """
    Get top N coins by 24h volume for a given quote currency.
    Filters out stablecoins, wrapped tokens, and leveraged tokens.
    """
    try:
        tickers = fetch_all_tickers()

        usdt_pairs = []
        for symbol, ticker in tickers.items():
            if symbol.endswith(f"/{quote}") and ticker.get("quoteVolume"):
                usdt_pairs.append((symbol, ticker["quoteVolume"]))

        usdt_pairs.sort(key=lambda x: x[1], reverse=True)

        excluded_bases = {
            "USDC", "BUSD", "DAI", "TUSD", "USDP", "FDUSD", "USDD",
            "WBTC", "WETH", "STETH",
        }
        excluded_suffixes = {"UP", "DOWN", "BULL", "BEAR", "3L", "3S", "2L", "2S"}

        filtered = []
        for symbol, vol in usdt_pairs:
            base = symbol.split("/")[0]
            if base in excluded_bases:
                continue
            if any(base.endswith(suffix) for suffix in excluded_suffixes):
                continue
            filtered.append(symbol)
            if len(filtered) >= n:
                break

        return filtered

    except Exception as e:
        logger.error(f"Error getting top coins: {e}")
        return []


def fetch_funding_rate(symbol: str) -> Optional[float]:
    """
    Fetch current funding rate for a perpetual futures symbol.
    Returns the funding rate as a decimal (e.g. 0.0001 = 0.01%).
    """
    try:
        exchange = get_futures_exchange()
        if exchange is None:
            return None

        # Convert spot symbol to futures if needed
        futures_symbol = symbol
        if not symbol.endswith(":USDT"):
            base = symbol.split("/")[0]
            futures_symbol = f"{base}/USDT:USDT"

        funding = exchange.fetch_funding_rate(futures_symbol)
        if funding and "fundingRate" in funding:
            return float(funding["fundingRate"])
        return None

    except Exception as e:
        logger.debug(f"Could not fetch funding rate for {symbol}: {e}")
        return None


def fetch_open_interest(symbol: str) -> Optional[float]:
    """
    Fetch open interest for a perpetual futures symbol.
    Returns open interest in quote currency value.
    """
    try:
        exchange = get_futures_exchange()
        if exchange is None:
            return None

        base = symbol.split("/")[0]
        futures_symbol = f"{base}/USDT:USDT"

        if hasattr(exchange, "fetch_open_interest"):
            oi = exchange.fetch_open_interest(futures_symbol)
            if oi and "openInterestValue" in oi:
                return float(oi["openInterestValue"])
        return None

    except Exception as e:
        logger.debug(f"Could not fetch open interest for {symbol}: {e}")
        return None


def fetch_ohlcv_history(
    symbol: str,
    timeframe: str = "1d",
    since: Optional[int] = None,
    limit: int = 1000,
) -> Optional[pd.DataFrame]:
    """
    Fetch historical OHLCV data (for backtesting).
    Can fetch larger datasets by paginating.
    """
    try:
        exchange = get_exchange()
        all_ohlcv = []
        current_since = since

        while len(all_ohlcv) < limit:
            batch_limit = min(500, limit - len(all_ohlcv))
            ohlcv = exchange.fetch_ohlcv(
                symbol, timeframe,
                since=current_since,
                limit=batch_limit,
            )
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            current_since = ohlcv[-1][0] + 1
            if len(ohlcv) < batch_limit:
                break

        if not all_ohlcv:
            return None

        df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)
        df = df[~df.index.duplicated(keep="first")]

        return df

    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {e}")
        return None
