"""
Strategy backtester.
Replays historical data through the same condition engine used by the live scanner.
"""
import logging
from typing import List, Optional, Dict
import pandas as pd
import numpy as np

from backend.scanner.data_fetcher import fetch_ohlcv_history
from backend.scanner.indicators import add_all_default_indicators
from backend.scanner.conditions import evaluate_condition
from backend.scanner.levels import calculate_key_levels

logger = logging.getLogger(__name__)

DEFAULT_FEE_BPS = 6.0
DEFAULT_SLIPPAGE_BPS = 4.0


def backtest_strategy(
    strategy_conditions: List[dict],
    direction: str,
    symbols: List[str],
    timeframe: str = "1d",
    lookback_bars: int = 365,
    evaluation_window: int = 50,
) -> dict:
    """
    Backtest a strategy across historical data.

    Args:
        strategy_conditions: List of condition dicts with keys:
            condition_type, timeframe, parameters, is_required
        direction: "long" or "short"
        symbols: List of symbols to test against
        timeframe: Primary timeframe for fetching data
        lookback_bars: How many bars of history to use
        evaluation_window: Minimum bars needed before first evaluation

    Returns:
        Dict with backtest results.
    """
    all_setups = []
    unique_timeframes = sorted(
        {c.get("timeframe", timeframe) for c in strategy_conditions} | {timeframe}
    )

    for symbol in symbols:
        try:
            tf_data: Dict[str, pd.DataFrame] = {}
            for tf in unique_timeframes:
                tf_df = fetch_ohlcv_history(symbol, tf, limit=lookback_bars)
                if tf_df is None or tf_df.empty:
                    tf_data = {}
                    break
                tf_data[tf] = add_all_default_indicators(tf_df)

            if not tf_data:
                continue

            primary_df = tf_data.get(timeframe)
            if primary_df is None or len(primary_df) < evaluation_window + 20:
                continue

            # Slide a window across the primary timeframe.
            for i in range(evaluation_window, len(primary_df) - 10):
                primary_window = primary_df.iloc[: i + 1].copy()
                signal_time = primary_window.index[-1]

                # Evaluate all required conditions on their own timeframe data
                # aligned to signal_time to avoid look-ahead bias.
                all_required_pass = True

                for cond in strategy_conditions:
                    if not cond.get("is_required", True):
                        continue

                    cond_tf = cond.get("timeframe", timeframe)
                    cond_df = tf_data.get(cond_tf)
                    if cond_df is None:
                        all_required_pass = False
                        break

                    cond_window = cond_df.loc[cond_df.index <= signal_time]
                    if cond_window is None or len(cond_window) < 2:
                        all_required_pass = False
                        break

                    result = evaluate_condition(
                        cond["condition_type"], cond_window, cond.get("parameters", {})
                    )
                    if not result:
                        all_required_pass = False
                        break

                if not all_required_pass:
                    continue

                # Setup detected at bar i — now check outcome.
                entry_price = float(primary_df.iloc[i]["close"])
                levels = calculate_key_levels(primary_window, direction, entry_price)

                # Simulate forward: did price hit TP1 or SL first?
                outcome = _simulate_forward(
                    primary_df.iloc[i + 1 : i + 11],  # Look ahead 10 bars
                    direction,
                    levels["entry_price"],
                    levels["stop_loss"],
                    levels["take_profit_1"],
                    levels.get("take_profit_2"),
                )

                all_setups.append(
                    {
                        "symbol": symbol,
                        "entry_date": str(primary_df.index[i]),
                        "entry_price": entry_price,
                        "stop_loss": levels["stop_loss"],
                        "take_profit_1": levels["take_profit_1"],
                        "take_profit_2": levels.get("take_profit_2"),
                        "risk_reward": levels["risk_reward_ratio"],
                        "outcome": outcome["result"],
                        "exit_price": outcome["exit_price"],
                        "pnl_r": outcome["pnl_r"],
                        "bars_held": outcome["bars_held"],
                    }
                )

        except Exception as e:
            logger.error(f"Backtest error for {symbol}: {e}")
            continue

    return _compile_results(all_setups, symbols, direction)


def _simulate_forward(
    future_df: pd.DataFrame,
    direction: str,
    entry: float,
    stop: float,
    tp1: float,
    tp2: Optional[float],
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict:
    """Simulate what happens after entry — does price hit TP or SL first?"""
    if future_df is None or len(future_df) == 0:
        return {"result": "expired", "exit_price": entry, "pnl_r": 0, "bars_held": 0}

    risk = abs(entry - stop) if abs(entry - stop) > 0 else entry * 0.01
    trading_cost_pct = (2.0 * (fee_bps + slippage_bps)) / 10000.0
    trading_cost_value = entry * trading_cost_pct

    for i, (_, row) in enumerate(future_df.iterrows()):
        high, low = float(row["high"]), float(row["low"])

        if direction == "long":
            if low <= stop:
                pnl = ((stop - entry) - trading_cost_value) / risk
                return {
                    "result": "loss",
                    "exit_price": stop,
                    "pnl_r": round(pnl, 2),
                    "bars_held": i + 1,
                }
            if high >= tp1:
                pnl = ((tp1 - entry) - trading_cost_value) / risk
                return {
                    "result": "win",
                    "exit_price": tp1,
                    "pnl_r": round(pnl, 2),
                    "bars_held": i + 1,
                }
        else:
            if high >= stop:
                pnl = ((entry - stop) - trading_cost_value) / risk
                return {
                    "result": "loss",
                    "exit_price": stop,
                    "pnl_r": round(pnl, 2),
                    "bars_held": i + 1,
                }
            if low <= tp1:
                pnl = ((entry - tp1) - trading_cost_value) / risk
                return {
                    "result": "win",
                    "exit_price": tp1,
                    "pnl_r": round(pnl, 2),
                    "bars_held": i + 1,
                }

    # No TP or SL hit within the forward window.
    last_close = float(future_df.iloc[-1]["close"])
    if direction == "long":
        pnl = ((last_close - entry) - trading_cost_value) / risk
    else:
        pnl = ((entry - last_close) - trading_cost_value) / risk

    return {
        "result": "expired",
        "exit_price": last_close,
        "pnl_r": round(pnl, 2),
        "bars_held": len(future_df),
    }


def _compile_results(setups: list, symbols: list, direction: str) -> dict:
    """Compile individual setup results into a summary."""
    if not setups:
        return {
            "strategy_name": "",
            "symbols_tested": len(symbols),
            "total_setups": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_rr": 0.0,
            "max_drawdown": 0.0,
            "setups_per_month": 0.0,
            "equity_curve": [],
            "setup_details": [],
        }

    try:
        setups = sorted(setups, key=lambda s: pd.Timestamp(s["entry_date"]))
    except Exception:
        pass

    wins = sum(1 for s in setups if s["outcome"] == "win")
    losses = sum(1 for s in setups if s["outcome"] == "loss")
    total = len(setups)
    win_rate = wins / total if total > 0 else 0

    r_values = [s["pnl_r"] for s in setups]
    avg_rr = np.mean(r_values) if r_values else 0

    # Equity curve (cumulative R)
    equity = [0.0]
    for r in r_values:
        equity.append(equity[-1] + r)

    # Max drawdown
    peak = 0
    max_dd = 0
    for val in equity:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    # Setups per month estimate
    if len(setups) >= 2:
        try:
            first_date = pd.Timestamp(setups[0]["entry_date"])
            last_date = pd.Timestamp(setups[-1]["entry_date"])
            months = max(1, (last_date - first_date).days / 30)
            setups_per_month = total / months
        except Exception:
            setups_per_month = 0
    else:
        setups_per_month = 0

    return {
        "strategy_name": "",
        "symbols_tested": len(symbols),
        "total_setups": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate * 100, 1),
        "avg_rr": round(float(avg_rr), 2),
        "max_drawdown": round(float(max_dd), 2),
        "setups_per_month": round(float(setups_per_month), 1),
        "equity_curve": [round(float(e), 2) for e in equity],
        "setup_details": setups[:100],  # Limit to 100 for response size
    }
