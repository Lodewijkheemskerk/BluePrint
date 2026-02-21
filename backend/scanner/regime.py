"""
Market regime detection.
Classifies the overall market state based on BTC price structure.
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
from backend.scanner.indicators import add_moving_average, add_ma_slope, add_atr


def detect_regime(btc_df: pd.DataFrame) -> Dict:
    """
    Detect current market regime based on BTC daily data.

    Returns dict with:
        regime: str - one of trending_up, trending_down, ranging, high_volatility
        description: str
        btc_trend: str
        confidence: float 0-1
        indicators: dict of supporting indicator values
    """
    if btc_df is None or len(btc_df) < 50:
        return {
            "regime": "ranging",
            "description": "Insufficient data — defaulting to ranging",
            "btc_trend": "unknown",
            "confidence": 0.0,
            "indicators": {},
        }

    df = btc_df.copy()
    df = add_moving_average(df, 50, "ema")
    df = add_moving_average(df, 200, "ema")
    df = add_ma_slope(df, 50, "ema", 5)
    df = add_ma_slope(df, 200, "ema", 5)
    df = add_atr(df, 14)

    last = df.iloc[-1]

    ema50 = last.get("ema_50")
    ema200 = last.get("ema_200")
    slope50 = last.get("ema_50_slope")
    slope200 = last.get("ema_200_slope")
    close = last["close"]
    atr = last.get("atr_14")

    # ATR as % of price
    atr_pct = (atr / close * 100) if (atr and close) else 0

    # Average ATR % over last 20 days
    df["atr_pct"] = df["atr_14"] / df["close"] * 100
    avg_atr_pct = df["atr_pct"].tail(20).mean() if "atr_14" in df.columns else 0

    indicators = {
        "ema_50": round(float(ema50), 2) if pd.notna(ema50) else None,
        "ema_200": round(float(ema200), 2) if pd.notna(ema200) else None,
        "ema_50_slope": round(float(slope50), 4) if pd.notna(slope50) else None,
        "ema_200_slope": round(float(slope200), 4) if pd.notna(slope200) else None,
        "close": round(float(close), 2),
        "atr_pct": round(float(atr_pct), 3),
        "avg_atr_pct": round(float(avg_atr_pct), 3),
    }

    # Check for high volatility first (ATR spike)
    if atr_pct > avg_atr_pct * 1.5 and atr_pct > 4.0:
        return {
            "regime": "high_volatility",
            "description": "High volatility environment — ATR is significantly elevated",
            "btc_trend": "volatile",
            "confidence": min(1.0, atr_pct / (avg_atr_pct * 2)),
            "indicators": indicators,
        }

    # Trending up: price above both MAs, slopes positive
    above_50 = close > ema50 if pd.notna(ema50) else False
    above_200 = close > ema200 if pd.notna(ema200) else False
    slope50_up = slope50 > 0 if pd.notna(slope50) else False
    slope200_up = slope200 > 0 if pd.notna(slope200) else False

    bullish_score = sum([above_50, above_200, slope50_up, slope200_up])
    bearish_score = sum([not above_50, not above_200,
                         (slope50 < 0 if pd.notna(slope50) else False),
                         (slope200 < 0 if pd.notna(slope200) else False)])

    if bullish_score >= 3:
        return {
            "regime": "trending_up",
            "description": "BTC in uptrend — price above key MAs with positive slope",
            "btc_trend": "bullish",
            "confidence": bullish_score / 4.0,
            "indicators": indicators,
        }

    if bearish_score >= 3:
        return {
            "regime": "trending_down",
            "description": "BTC in downtrend — price below key MAs with negative slope",
            "btc_trend": "bearish",
            "confidence": bearish_score / 4.0,
            "indicators": indicators,
        }

    return {
        "regime": "ranging",
        "description": "BTC in range-bound/indecisive state — mixed signals",
        "btc_trend": "neutral",
        "confidence": 0.5,
        "indicators": indicators,
    }
