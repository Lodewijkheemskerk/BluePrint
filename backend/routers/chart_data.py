"""
Chart data endpoints for the frontend TradingView Lightweight Charts.
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from backend.scanner.data_fetcher import fetch_ohlcv, fetch_funding_rate

router = APIRouter(prefix="/api/chart", tags=["chart"])


@router.get("/ohlcv/{symbol}")
def get_ohlcv(
    symbol: str,
    timeframe: str = Query(default="1d"),
    limit: int = Query(default=200, le=500),
):
    """Get OHLCV data formatted for TradingView Lightweight Charts."""
    # Convert URL-safe symbol back to standard format
    clean_symbol = symbol.replace("-", "/")

    df = fetch_ohlcv(clean_symbol, timeframe, limit)
    if df is None:
        return {"candles": [], "volumes": []}

    candles = []
    volumes = []
    for idx, row in df.iterrows():
        ts = int(idx.timestamp())
        candles.append({
            "time": ts,
            "open": round(float(row["open"]), 8),
            "high": round(float(row["high"]), 8),
            "low": round(float(row["low"]), 8),
            "close": round(float(row["close"]), 8),
        })
        color = "#089981" if row["close"] >= row["open"] else "#f23645"
        volumes.append({
            "time": ts,
            "value": round(float(row["volume"]), 2),
            "color": color,
        })

    return {"candles": candles, "volumes": volumes}


@router.get("/funding/{symbol}")
def get_funding(symbol: str):
    """Get current funding rate for a symbol."""
    clean_symbol = symbol.replace("-", "/")
    rate = fetch_funding_rate(clean_symbol)
    return {"symbol": clean_symbol, "funding_rate": rate}
