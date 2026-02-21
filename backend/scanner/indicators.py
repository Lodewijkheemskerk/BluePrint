"""
Technical indicator calculations using the `ta` library.
All functions take an OHLCV DataFrame and return the DataFrame with added columns.
"""
import pandas as pd
import numpy as np
from typing import Optional


def add_moving_average(df: pd.DataFrame, period: int = 50, ma_type: str = "ema") -> pd.DataFrame:
    """Add a moving average column."""
    col_name = f"{ma_type}_{period}"
    if col_name in df.columns:
        return df

    if ma_type == "ema":
        df[col_name] = df["close"].ewm(span=period, adjust=False).mean()
    elif ma_type == "sma":
        df[col_name] = df["close"].rolling(window=period).mean()
    return df


def add_ma_slope(df: pd.DataFrame, period: int = 50, ma_type: str = "ema", lookback: int = 5) -> pd.DataFrame:
    """Add MA slope (rate of change over lookback period)."""
    ma_col = f"{ma_type}_{period}"
    slope_col = f"{ma_col}_slope"

    if slope_col in df.columns:
        return df

    df = add_moving_average(df, period, ma_type)
    if ma_col in df.columns:
        df[slope_col] = df[ma_col].diff(lookback)
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add RSI indicator."""
    col_name = f"rsi_{period}"
    if col_name in df.columns:
        return df

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
    df[col_name] = 100 - (100 / (1 + rs))
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Add MACD indicator (line, histogram, signal)."""
    prefix = f"macd_{fast}_{slow}_{signal}"
    if f"{prefix}_hist" in df.columns:
        return df

    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    df[f"{prefix}_line"] = macd_line
    df[f"{prefix}_signal"] = signal_line
    df[f"{prefix}_hist"] = histogram
    return df


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """Add Bollinger Bands and bandwidth."""
    prefix = f"bb_{period}"
    if f"{prefix}_upper" in df.columns:
        return df

    mid = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()

    df[f"{prefix}_upper"] = mid + std_dev * std
    df[f"{prefix}_mid"] = mid
    df[f"{prefix}_lower"] = mid - std_dev * std
    df[f"{prefix}_bandwidth"] = (df[f"{prefix}_upper"] - df[f"{prefix}_lower"]) / mid
    df[f"{prefix}_pctb"] = (df["close"] - df[f"{prefix}_lower"]) / (df[f"{prefix}_upper"] - df[f"{prefix}_lower"])
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add Average True Range."""
    col_name = f"atr_{period}"
    if col_name in df.columns:
        return df

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df[col_name] = tr.ewm(span=period, adjust=False).mean()
    return df


def add_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Add volume simple moving average."""
    col_name = f"vol_sma_{period}"
    if col_name in df.columns:
        return df

    df[col_name] = df["volume"].rolling(window=period).mean()
    return df


def add_all_default_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add a comprehensive set of default indicators."""
    df = add_moving_average(df, 20, "ema")
    df = add_moving_average(df, 50, "ema")
    df = add_moving_average(df, 200, "ema")
    df = add_moving_average(df, 50, "sma")
    df = add_moving_average(df, 200, "sma")
    df = add_ma_slope(df, 50, "ema", 5)
    df = add_ma_slope(df, 200, "ema", 5)
    df = add_rsi(df, 14)
    df = add_macd(df)
    df = add_bollinger_bands(df, 20, 2.0)
    df = add_atr(df, 14)
    df = add_volume_sma(df, 20)
    return df
