"""
Key level calculation: entry zones, stop-loss, take-profit targets.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from backend.scanner.indicators import add_atr
from backend.scanner.conditions import _find_swing_highs, _find_swing_lows


def calculate_key_levels(
    df: pd.DataFrame,
    direction: str,
    current_price: float,
) -> Dict[str, Optional[float]]:
    """
    Calculate entry, stop-loss, and take-profit levels for a setup.

    Args:
        df: OHLCV DataFrame (entry timeframe)
        direction: "long" or "short"
        current_price: Current price of the asset

    Returns:
        Dict with entry_price, stop_loss, take_profit_1, take_profit_2,
        take_profit_3, risk_reward_ratio
    """
    df = add_atr(df, 14)
    atr = df.iloc[-1].get("atr_14", 0)
    if pd.isna(atr) or atr == 0:
        atr = current_price * 0.02  # fallback: 2% of price

    swing_highs = _find_swing_highs(df.tail(50), window=3)
    swing_lows = _find_swing_lows(df.tail(50), window=3)

    if direction == "long":
        return _calc_long_levels(current_price, atr, swing_highs, swing_lows)
    else:
        return _calc_short_levels(current_price, atr, swing_highs, swing_lows)


def _calc_long_levels(price: float, atr: float,
                      swing_highs: list, swing_lows: list) -> dict:
    """Calculate levels for a long setup."""
    # Entry: current price (or slightly below)
    entry = price

    # Stop loss: below recent swing low, or 1.5 ATR below entry
    if swing_lows:
        # Find the nearest swing low below current price
        below_lows = [l for l in swing_lows if l < price]
        if below_lows:
            stop = below_lows[-1] - atr * 0.2  # small buffer below swing low
        else:
            stop = price - atr * 1.5
    else:
        stop = price - atr * 1.5

    risk = entry - stop
    if risk <= 0:
        risk = atr

    # Take profit targets at 1.5R, 2.5R, 4R
    tp1 = entry + risk * 1.5
    tp2 = entry + risk * 2.5
    tp3 = entry + risk * 4.0

    # Adjust TP levels to nearby resistance if available
    if swing_highs:
        above_highs = sorted([h for h in swing_highs if h > price])
        if len(above_highs) >= 1:
            tp1 = max(tp1, above_highs[0])
        if len(above_highs) >= 2:
            tp2 = max(tp2, above_highs[1])

    rr = (tp1 - entry) / risk if risk > 0 else 0

    return {
        "entry_price": round(entry, 8),
        "stop_loss": round(stop, 8),
        "take_profit_1": round(tp1, 8),
        "take_profit_2": round(tp2, 8),
        "take_profit_3": round(tp3, 8),
        "risk_reward_ratio": round(rr, 2),
    }


def _calc_short_levels(price: float, atr: float,
                       swing_highs: list, swing_lows: list) -> dict:
    """Calculate levels for a short setup."""
    entry = price

    # Stop loss: above recent swing high, or 1.5 ATR above entry
    if swing_highs:
        above_highs = [h for h in swing_highs if h > price]
        if above_highs:
            stop = above_highs[0] + atr * 0.2
        else:
            stop = price + atr * 1.5
    else:
        stop = price + atr * 1.5

    risk = stop - entry
    if risk <= 0:
        risk = atr

    tp1 = entry - risk * 1.5
    tp2 = entry - risk * 2.5
    tp3 = entry - risk * 4.0

    if swing_lows:
        below_lows = sorted([l for l in swing_lows if l < price], reverse=True)
        if len(below_lows) >= 1:
            tp1 = min(tp1, below_lows[0])
        if len(below_lows) >= 2:
            tp2 = min(tp2, below_lows[1])

    rr = (entry - tp1) / risk if risk > 0 else 0

    return {
        "entry_price": round(entry, 8),
        "stop_loss": round(stop, 8),
        "take_profit_1": round(max(0, tp1), 8),
        "take_profit_2": round(max(0, tp2), 8),
        "take_profit_3": round(max(0, tp3), 8),
        "risk_reward_ratio": round(rr, 2),
    }
