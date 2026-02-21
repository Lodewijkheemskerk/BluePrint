"""
Condition evaluation engine.
Each condition_type maps to a function that takes a DataFrame and parameters,
returning True/False for whether the condition is met.
"""
import pandas as pd
import numpy as np
from typing import Callable, Dict, Optional, Any
from backend.scanner.indicators import (
    add_moving_average, add_ma_slope, add_rsi, add_macd,
    add_bollinger_bands, add_atr, add_volume_sma
)

# Registry of condition evaluators
CONDITION_REGISTRY: Dict[str, Callable] = {}


def register_condition(name: str, category: str, description: str,
                       params_schema: dict, default_tf: str = "1d"):
    """Decorator to register a condition evaluator."""
    def decorator(func):
        func._condition_meta = {
            "type": name,
            "category": category,
            "description": description,
            "parameters": params_schema,
            "default_timeframe": default_tf,
        }
        CONDITION_REGISTRY[name] = func
        return func
    return decorator


def evaluate_condition(condition_type: str, df: pd.DataFrame, params: dict) -> bool:
    """Evaluate a single condition against OHLCV data."""
    if condition_type not in CONDITION_REGISTRY:
        raise ValueError(f"Unknown condition type: {condition_type}")
    if df is None or df.empty or len(df) < 2:
        return False
    try:
        return CONDITION_REGISTRY[condition_type](df, params)
    except Exception:
        return False


def get_condition_types() -> list:
    """Return metadata for all registered condition types."""
    result = []
    for func in CONDITION_REGISTRY.values():
        if hasattr(func, "_condition_meta"):
            result.append(func._condition_meta)
    return result


# ──── TREND CONDITIONS ────────────────────────────────────────────────────────

@register_condition(
    "price_above_ma", "trend",
    "Price is above a moving average",
    {"period": 50, "ma_type": "ema"}, "1d"
)
def cond_price_above_ma(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 50)
    ma_type = params.get("ma_type", "ema")
    df = add_moving_average(df, period, ma_type)
    col = f"{ma_type}_{period}"
    if col not in df.columns:
        return False
    last = df.iloc[-1]
    return bool(last["close"] > last[col]) if pd.notna(last[col]) else False


@register_condition(
    "price_below_ma", "trend",
    "Price is below a moving average",
    {"period": 50, "ma_type": "ema"}, "1d"
)
def cond_price_below_ma(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 50)
    ma_type = params.get("ma_type", "ema")
    df = add_moving_average(df, period, ma_type)
    col = f"{ma_type}_{period}"
    if col not in df.columns:
        return False
    last = df.iloc[-1]
    return bool(last["close"] < last[col]) if pd.notna(last[col]) else False


@register_condition(
    "ma_slope_rising", "trend",
    "Moving average slope is positive (rising)",
    {"period": 50, "ma_type": "ema", "lookback": 5}, "1d"
)
def cond_ma_slope_rising(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 50)
    ma_type = params.get("ma_type", "ema")
    lookback = params.get("lookback", 5)
    df = add_ma_slope(df, period, ma_type, lookback)
    col = f"{ma_type}_{period}_slope"
    if col not in df.columns:
        return False
    val = df.iloc[-1][col]
    return bool(val > 0) if pd.notna(val) else False


@register_condition(
    "ma_slope_falling", "trend",
    "Moving average slope is negative (falling)",
    {"period": 50, "ma_type": "ema", "lookback": 5}, "1d"
)
def cond_ma_slope_falling(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 50)
    ma_type = params.get("ma_type", "ema")
    lookback = params.get("lookback", 5)
    df = add_ma_slope(df, period, ma_type, lookback)
    col = f"{ma_type}_{period}_slope"
    if col not in df.columns:
        return False
    val = df.iloc[-1][col]
    return bool(val < 0) if pd.notna(val) else False


@register_condition(
    "ema_crossover_bullish", "trend",
    "Fast EMA crossed above slow EMA",
    {"fast_period": 20, "slow_period": 50}, "1d"
)
def cond_ema_crossover_bullish(df: pd.DataFrame, params: dict) -> bool:
    fast = params.get("fast_period", 20)
    slow = params.get("slow_period", 50)
    df = add_moving_average(df, fast, "ema")
    df = add_moving_average(df, slow, "ema")
    fast_col, slow_col = f"ema_{fast}", f"ema_{slow}"
    if fast_col not in df.columns or slow_col not in df.columns:
        return False
    if len(df) < 2:
        return False
    curr_fast, curr_slow = df.iloc[-1][fast_col], df.iloc[-1][slow_col]
    prev_fast, prev_slow = df.iloc[-2][fast_col], df.iloc[-2][slow_col]
    if any(pd.isna(v) for v in [curr_fast, curr_slow, prev_fast, prev_slow]):
        return False
    return bool(prev_fast <= prev_slow and curr_fast > curr_slow)


@register_condition(
    "ema_crossover_bearish", "trend",
    "Fast EMA crossed below slow EMA",
    {"fast_period": 20, "slow_period": 50}, "1d"
)
def cond_ema_crossover_bearish(df: pd.DataFrame, params: dict) -> bool:
    fast = params.get("fast_period", 20)
    slow = params.get("slow_period", 50)
    df = add_moving_average(df, fast, "ema")
    df = add_moving_average(df, slow, "ema")
    fast_col, slow_col = f"ema_{fast}", f"ema_{slow}"
    if fast_col not in df.columns or slow_col not in df.columns:
        return False
    if len(df) < 2:
        return False
    curr_fast, curr_slow = df.iloc[-1][fast_col], df.iloc[-1][slow_col]
    prev_fast, prev_slow = df.iloc[-2][fast_col], df.iloc[-2][slow_col]
    if any(pd.isna(v) for v in [curr_fast, curr_slow, prev_fast, prev_slow]):
        return False
    return bool(prev_fast >= prev_slow and curr_fast < curr_slow)


@register_condition(
    "higher_highs_higher_lows", "trend",
    "Recent price structure shows higher highs and higher lows (uptrend)",
    {"lookback": 20, "min_swings": 2}, "1d"
)
def cond_hh_hl(df: pd.DataFrame, params: dict) -> bool:
    lookback = params.get("lookback", 20)
    min_swings = params.get("min_swings", 2)
    recent = df.tail(lookback)
    if len(recent) < 10:
        return False
    highs = _find_swing_highs(recent, window=3)
    lows = _find_swing_lows(recent, window=3)
    if len(highs) < min_swings or len(lows) < min_swings:
        return False
    hh = all(highs[i] < highs[i + 1] for i in range(len(highs) - 1))
    hl = all(lows[i] < lows[i + 1] for i in range(len(lows) - 1))
    return bool(hh and hl)


@register_condition(
    "lower_highs_lower_lows", "trend",
    "Recent price structure shows lower highs and lower lows (downtrend)",
    {"lookback": 20, "min_swings": 2}, "1d"
)
def cond_lh_ll(df: pd.DataFrame, params: dict) -> bool:
    lookback = params.get("lookback", 20)
    min_swings = params.get("min_swings", 2)
    recent = df.tail(lookback)
    if len(recent) < 10:
        return False
    highs = _find_swing_highs(recent, window=3)
    lows = _find_swing_lows(recent, window=3)
    if len(highs) < min_swings or len(lows) < min_swings:
        return False
    lh = all(highs[i] > highs[i + 1] for i in range(len(highs) - 1))
    ll = all(lows[i] > lows[i + 1] for i in range(len(lows) - 1))
    return bool(lh and ll)


# ──── MARKET STRUCTURE CONDITIONS ─────────────────────────────────────────────

@register_condition(
    "break_of_structure_bullish", "structure",
    "Price broke above a recent swing high",
    {"lookback": 20, "swing_window": 5}, "4h"
)
def cond_bos_bullish(df: pd.DataFrame, params: dict) -> bool:
    lookback = params.get("lookback", 20)
    swing_window = params.get("swing_window", 5)
    recent = df.tail(lookback + 1)
    if len(recent) < lookback:
        return False
    older = recent.iloc[:-1]
    highs = _find_swing_highs(older, window=swing_window)
    if not highs:
        return False
    last_swing_high = highs[-1]
    return bool(df.iloc[-1]["close"] > last_swing_high)


@register_condition(
    "break_of_structure_bearish", "structure",
    "Price broke below a recent swing low",
    {"lookback": 20, "swing_window": 5}, "4h"
)
def cond_bos_bearish(df: pd.DataFrame, params: dict) -> bool:
    lookback = params.get("lookback", 20)
    swing_window = params.get("swing_window", 5)
    recent = df.tail(lookback + 1)
    if len(recent) < lookback:
        return False
    older = recent.iloc[:-1]
    lows = _find_swing_lows(older, window=swing_window)
    if not lows:
        return False
    last_swing_low = lows[-1]
    return bool(df.iloc[-1]["close"] < last_swing_low)


@register_condition(
    "price_near_support", "structure",
    "Price is within X% of a detected support zone",
    {"lookback": 50, "proximity_pct": 2.0, "swing_window": 5}, "4h"
)
def cond_price_near_support(df: pd.DataFrame, params: dict) -> bool:
    lookback = params.get("lookback", 50)
    proximity = params.get("proximity_pct", 2.0) / 100.0
    swing_window = params.get("swing_window", 5)
    recent = df.tail(lookback)
    lows = _find_swing_lows(recent, window=swing_window)
    if not lows:
        return False
    current_price = df.iloc[-1]["close"]
    for level in reversed(lows):
        if level < current_price:
            distance = (current_price - level) / current_price
            if distance <= proximity:
                return True
    return False


@register_condition(
    "price_near_resistance", "structure",
    "Price is within X% of a detected resistance zone",
    {"lookback": 50, "proximity_pct": 2.0, "swing_window": 5}, "4h"
)
def cond_price_near_resistance(df: pd.DataFrame, params: dict) -> bool:
    lookback = params.get("lookback", 50)
    proximity = params.get("proximity_pct", 2.0) / 100.0
    swing_window = params.get("swing_window", 5)
    recent = df.tail(lookback)
    highs = _find_swing_highs(recent, window=swing_window)
    if not highs:
        return False
    current_price = df.iloc[-1]["close"]
    for level in reversed(highs):
        if level > current_price:
            distance = (level - current_price) / current_price
            if distance <= proximity:
                return True
    return False


# ──── VOLATILITY CONDITIONS ───────────────────────────────────────────────────

@register_condition(
    "bb_squeeze", "volatility",
    "Bollinger Band bandwidth is below threshold (squeeze/contraction)",
    {"period": 20, "std_dev": 2.0, "threshold": 0.05}, "4h"
)
def cond_bb_squeeze(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 20)
    std_dev = params.get("std_dev", 2.0)
    threshold = params.get("threshold", 0.05)
    df = add_bollinger_bands(df, period, std_dev)
    bw_col = f"bb_{period}_bandwidth"
    if bw_col not in df.columns:
        return False
    val = df.iloc[-1][bw_col]
    return bool(val < threshold) if pd.notna(val) else False


@register_condition(
    "atr_above_average", "volatility",
    "ATR is above its own moving average (enough volatility)",
    {"atr_period": 14, "avg_period": 20}, "4h"
)
def cond_atr_above_avg(df: pd.DataFrame, params: dict) -> bool:
    atr_period = params.get("atr_period", 14)
    avg_period = params.get("avg_period", 20)
    df = add_atr(df, atr_period)
    atr_col = f"atr_{atr_period}"
    if atr_col not in df.columns:
        return False
    atr_avg = df[atr_col].rolling(avg_period).mean()
    if pd.isna(atr_avg.iloc[-1]):
        return False
    return bool(df.iloc[-1][atr_col] > atr_avg.iloc[-1])


@register_condition(
    "atr_below_average", "volatility",
    "ATR is below its own moving average (low volatility)",
    {"atr_period": 14, "avg_period": 20}, "4h"
)
def cond_atr_below_avg(df: pd.DataFrame, params: dict) -> bool:
    atr_period = params.get("atr_period", 14)
    avg_period = params.get("avg_period", 20)
    df = add_atr(df, atr_period)
    atr_col = f"atr_{atr_period}"
    if atr_col not in df.columns:
        return False
    atr_avg = df[atr_col].rolling(avg_period).mean()
    if pd.isna(atr_avg.iloc[-1]):
        return False
    return bool(df.iloc[-1][atr_col] < atr_avg.iloc[-1])


@register_condition(
    "candle_range_contraction", "volatility",
    "Recent candle ranges are smaller than average",
    {"lookback": 5, "avg_period": 20, "ratio": 0.7}, "4h"
)
def cond_candle_contraction(df: pd.DataFrame, params: dict) -> bool:
    lookback = params.get("lookback", 5)
    avg_period = params.get("avg_period", 20)
    ratio = params.get("ratio", 0.7)
    df["_range"] = df["high"] - df["low"]
    avg_range = df["_range"].rolling(avg_period).mean()
    recent_avg = df["_range"].tail(lookback).mean()
    if pd.isna(avg_range.iloc[-1]) or avg_range.iloc[-1] == 0:
        return False
    return bool(recent_avg / avg_range.iloc[-1] < ratio)


# ──── MOMENTUM CONDITIONS ─────────────────────────────────────────────────────

@register_condition(
    "rsi_in_range", "momentum",
    "RSI is within a specified range",
    {"period": 14, "min_val": 30, "max_val": 50}, "4h"
)
def cond_rsi_in_range(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 14)
    min_val = params.get("min_val", 30)
    max_val = params.get("max_val", 50)
    df = add_rsi(df, period)
    col = f"rsi_{period}"
    if col not in df.columns:
        return False
    val = df.iloc[-1][col]
    return bool(min_val <= val <= max_val) if pd.notna(val) else False


@register_condition(
    "rsi_oversold", "momentum",
    "RSI is below oversold threshold",
    {"period": 14, "threshold": 30}, "4h"
)
def cond_rsi_oversold(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 14)
    threshold = params.get("threshold", 30)
    df = add_rsi(df, period)
    col = f"rsi_{period}"
    if col not in df.columns:
        return False
    val = df.iloc[-1][col]
    return bool(val < threshold) if pd.notna(val) else False


@register_condition(
    "rsi_overbought", "momentum",
    "RSI is above overbought threshold",
    {"period": 14, "threshold": 70}, "4h"
)
def cond_rsi_overbought(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 14)
    threshold = params.get("threshold", 70)
    df = add_rsi(df, period)
    col = f"rsi_{period}"
    if col not in df.columns:
        return False
    val = df.iloc[-1][col]
    return bool(val > threshold) if pd.notna(val) else False


@register_condition(
    "macd_histogram_positive", "momentum",
    "MACD histogram is positive (bullish momentum)",
    {"fast": 12, "slow": 26, "signal": 9}, "4h"
)
def cond_macd_hist_positive(df: pd.DataFrame, params: dict) -> bool:
    fast = params.get("fast", 12)
    slow = params.get("slow", 26)
    signal = params.get("signal", 9)
    df = add_macd(df, fast, slow, signal)
    col = f"macd_{fast}_{slow}_{signal}_hist"
    if col not in df.columns:
        return False
    val = df.iloc[-1][col]
    return bool(val > 0) if pd.notna(val) else False


@register_condition(
    "macd_histogram_negative", "momentum",
    "MACD histogram is negative (bearish momentum)",
    {"fast": 12, "slow": 26, "signal": 9}, "4h"
)
def cond_macd_hist_negative(df: pd.DataFrame, params: dict) -> bool:
    fast = params.get("fast", 12)
    slow = params.get("slow", 26)
    signal = params.get("signal", 9)
    df = add_macd(df, fast, slow, signal)
    col = f"macd_{fast}_{slow}_{signal}_hist"
    if col not in df.columns:
        return False
    val = df.iloc[-1][col]
    return bool(val < 0) if pd.notna(val) else False


@register_condition(
    "rsi_bullish_divergence", "momentum",
    "Price made a lower low but RSI made a higher low (bullish divergence)",
    {"period": 14, "lookback": 20}, "4h"
)
def cond_rsi_bull_div(df: pd.DataFrame, params: dict) -> bool:
    period = params.get("period", 14)
    lookback = params.get("lookback", 20)
    df = add_rsi(df, period)
    col = f"rsi_{period}"
    if col not in df.columns or len(df) < lookback:
        return False
    recent = df.tail(lookback)
    price_lows = _find_swing_lows(recent, window=3, col="close")
    rsi_vals = recent[col].values
    rsi_low_indices = _find_swing_low_indices(recent, window=3, col=col)
    if len(price_lows) < 2 or len(rsi_low_indices) < 2:
        return False
    price_ll = price_lows[-1] < price_lows[-2]
    rsi_hl = rsi_vals[rsi_low_indices[-1]] > rsi_vals[rsi_low_indices[-2]]
    return bool(price_ll and rsi_hl)


# ──── VOLUME CONDITIONS ───────────────────────────────────────────────────────

@register_condition(
    "volume_spike", "volume",
    "Current volume is X times the average volume",
    {"avg_period": 20, "multiplier": 2.0}, "4h"
)
def cond_volume_spike(df: pd.DataFrame, params: dict) -> bool:
    avg_period = params.get("avg_period", 20)
    multiplier = params.get("multiplier", 2.0)
    df = add_volume_sma(df, avg_period)
    vol_col = f"vol_sma_{avg_period}"
    if vol_col not in df.columns:
        return False
    avg_vol = df.iloc[-1][vol_col]
    if pd.isna(avg_vol) or avg_vol == 0:
        return False
    return bool(df.iloc[-1]["volume"] > avg_vol * multiplier)


@register_condition(
    "volume_declining", "volume",
    "Volume has been declining over the last N candles",
    {"candles": 3}, "4h"
)
def cond_volume_declining(df: pd.DataFrame, params: dict) -> bool:
    candles = params.get("candles", 3)
    if len(df) < candles + 1:
        return False
    recent_vols = df["volume"].tail(candles + 1).values
    for i in range(1, len(recent_vols)):
        if recent_vols[i] >= recent_vols[i - 1]:
            return False
    return True


# ──── FUNDING / SENTIMENT CONDITIONS ──────────────────────────────────────────

@register_condition(
    "funding_rate_below", "funding",
    "Funding rate is below a threshold (not overcrowded long)",
    {"threshold": 0.01}, "1d"
)
def cond_funding_below(df: pd.DataFrame, params: dict) -> bool:
    threshold = params.get("threshold", 0.01)
    if "_funding_rate" not in df.columns:
        return True  # If no funding data, pass by default
    val = df.iloc[-1].get("_funding_rate")
    return bool(val < threshold) if pd.notna(val) else True


@register_condition(
    "funding_rate_above", "funding",
    "Funding rate is above a threshold (not overcrowded short)",
    {"threshold": -0.01}, "1d"
)
def cond_funding_above(df: pd.DataFrame, params: dict) -> bool:
    threshold = params.get("threshold", -0.01)
    if "_funding_rate" not in df.columns:
        return True
    val = df.iloc[-1].get("_funding_rate")
    return bool(val > threshold) if pd.notna(val) else True


@register_condition(
    "open_interest_rising", "funding",
    "Open interest has been rising over the last N candles",
    {"candles": 3}, "1d"
)
def cond_oi_rising(df: pd.DataFrame, params: dict) -> bool:
    candles = params.get("candles", 3)
    if "_open_interest" not in df.columns:
        return True
    recent = df["_open_interest"].tail(candles + 1).dropna()
    if len(recent) < candles + 1:
        return True
    vals = recent.values
    return bool(all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)))


# ──── HELPERS ─────────────────────────────────────────────────────────────────

def _find_swing_highs(df: pd.DataFrame, window: int = 3, col: str = "high") -> list:
    """Find swing high values in a DataFrame."""
    values = df[col].values
    highs = []
    for i in range(window, len(values) - window):
        if all(values[i] >= values[i - j] for j in range(1, window + 1)) and \
           all(values[i] >= values[i + j] for j in range(1, window + 1)):
            highs.append(float(values[i]))
    return highs


def _find_swing_lows(df: pd.DataFrame, window: int = 3, col: str = "low") -> list:
    """Find swing low values in a DataFrame."""
    values = df[col].values
    lows = []
    for i in range(window, len(values) - window):
        if all(values[i] <= values[i - j] for j in range(1, window + 1)) and \
           all(values[i] <= values[i + j] for j in range(1, window + 1)):
            lows.append(float(values[i]))
    return lows


def _find_swing_low_indices(df: pd.DataFrame, window: int = 3, col: str = "low") -> list:
    """Find swing low indices in a DataFrame."""
    values = df[col].values
    indices = []
    for i in range(window, len(values) - window):
        if all(values[i] <= values[i - j] for j in range(1, window + 1)) and \
           all(values[i] <= values[i + j] for j in range(1, window + 1)):
            indices.append(i)
    return indices
