"""
Main scanning engine - orchestrates the full scan cycle.
"""
import json
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Tuple

from sqlalchemy.orm import Session

from backend.models import (
    Asset,
    Strategy,
    Setup,
    ScanLog,
    SetupStatus,
    Direction,
    AssetSource,
)
from backend.scanner.data_fetcher import (
    fetch_ohlcv,
    fetch_multi_timeframe,
    get_top_coins_by_volume,
    fetch_funding_rate,
    fetch_open_interest,
)
from backend.scanner.indicators import add_all_default_indicators
from backend.scanner.conditions import evaluate_condition
from backend.scanner.regime import detect_regime
from backend.scanner.levels import calculate_key_levels
from backend.config import settings

logger = logging.getLogger(__name__)

SETUP_EXPIRY_HOURS = 48

_scan_lock = threading.Lock()
_scan_running = False
_scan_cancelled = False
_current_scan_log_id = None


def run_scan(db: Session, scan_id: Optional[int] = None) -> ScanLog:
    """
    Execute a full scan cycle.

    1. Refresh universe
    2. Detect market regime (BTC)
    3. For each asset, evaluate all active strategies
    4. Generate setups where conditions match
    5. Update lifecycle of existing setups
    """
    global _scan_running, _scan_cancelled, _current_scan_log_id

    _scan_cancelled = False

    if not _scan_lock.acquire(blocking=False):
        logger.warning("Scan already in progress - skipping duplicate scan request")
        existing_log = db.query(ScanLog).order_by(ScanLog.id.desc()).first()
        if existing_log:
            return existing_log
        scan_log = ScanLog(
            started_at=datetime.now(timezone.utc),
            status="skipped",
            finished_at=datetime.now(timezone.utc),
            errors=json.dumps(["Scan skipped - another scan is already running"]),
        )
        db.add(scan_log)
        db.commit()
        return scan_log

    try:
        _scan_running = True
        logger.info("Starting scan (lock acquired)")

        if scan_id:
            scan_log = db.query(ScanLog).filter(ScanLog.id == scan_id).first()
            if not scan_log:
                logger.warning(f"Scan log {scan_id} not found, creating new one")
                scan_log = ScanLog(started_at=datetime.now(timezone.utc))
                db.add(scan_log)
                db.commit()
            _current_scan_log_id = scan_log.id
        else:
            scan_log = ScanLog(started_at=datetime.now(timezone.utc))
            db.add(scan_log)
            db.commit()
            _current_scan_log_id = scan_log.id

        errors = []

        try:
            if _scan_cancelled:
                raise InterruptedError("Scan was cancelled before starting")

            _refresh_dynamic_universe(db)

            if _scan_cancelled:
                raise InterruptedError("Scan was cancelled during universe refresh")

            btc_df = fetch_ohlcv("BTC/USDT", "1d", 200)
            if btc_df is None:
                logger.warning("Failed to fetch BTC data for regime detection - scan may be incomplete")
                errors.append("Failed to fetch BTC data for regime detection")
            regime_info = detect_regime(btc_df)
            current_regime = regime_info["regime"]
            scan_log.market_regime = current_regime
            logger.info(f"Market regime: {current_regime}")

            if _scan_cancelled:
                raise InterruptedError("Scan was cancelled during regime detection")

            assets = db.query(Asset).filter(Asset.is_active == True).all()
            strategies = db.query(Strategy).filter(Strategy.is_active == True).all()

            valid_strategies = []
            for strat in strategies:
                regimes = strat.regime_list
                if regimes is None or current_regime in regimes:
                    valid_strategies.append(strat)

            logger.info(f"Scanning {len(assets)} assets with {len(valid_strategies)} strategies")

            if len(assets) == 0:
                logger.warning("No active assets to scan - check if universe refresh succeeded")
                errors.append("No active assets found to scan")
            if len(valid_strategies) == 0:
                logger.warning("No valid strategies to evaluate - check strategy configuration")
                errors.append("No valid strategies found to evaluate")

            setups_found = 0
            assets_scanned = 0

            for asset in assets:
                if _scan_cancelled:
                    logger.info(f"Scan cancelled - processed {assets_scanned}/{len(assets)} assets")
                    raise InterruptedError("Scan was cancelled by user")

                try:
                    asset_setups = _evaluate_asset(
                        db, asset, valid_strategies, current_regime, scan_log.id
                    )
                    setups_found += asset_setups
                    assets_scanned += 1
                except Exception as e:
                    err = f"Error scanning {asset.symbol}: {str(e)}"
                    logger.error(err)
                    errors.append(err)
                    assets_scanned += 1

            scan_log.assets_scanned = assets_scanned

            if _scan_cancelled:
                raise InterruptedError("Scan was cancelled after asset evaluation")

            scan_log.setups_found = setups_found

            expired, invalidated = _update_setup_lifecycle(db)
            scan_log.setups_expired = expired
            scan_log.setups_invalidated = invalidated

            scan_log.status = "completed"
            logger.info(
                f"Scan complete: {assets_scanned} assets, {setups_found} new setups, "
                f"{expired} expired, {invalidated} invalidated"
            )

        except InterruptedError as e:
            scan_log.status = "cancelled"
            errors.append(f"Scan cancelled: {str(e)}")
            logger.info(f"Scan cancelled: {e}")
        except Exception as e:
            scan_log.status = "failed"
            errors.append(f"Scan failed: {str(e)}")
            logger.error(f"Scan failed: {e}")

        scan_log.finished_at = datetime.now(timezone.utc)
        scan_log.errors = json.dumps(errors) if errors else None
        db.commit()
        db.refresh(scan_log)

        return scan_log
    finally:
        _scan_running = False
        _scan_cancelled = False
        _current_scan_log_id = None
        _scan_lock.release()
        logger.info("Scan completed (lock released)")


def cancel_scan() -> bool:
    """Cancel the currently running scan."""
    global _scan_cancelled, _scan_running

    if not _scan_running:
        logger.warning("No scan is currently running to cancel")
        return False

    _scan_cancelled = True
    logger.info("Scan cancellation requested")
    return True


def is_scan_running() -> bool:
    """Check if a scan is currently running."""
    return _scan_running


def get_current_scan_id() -> Optional[int]:
    """Get the ID of the currently running scan, or None if no scan is running."""
    return _current_scan_log_id if _scan_running else None


def _refresh_dynamic_universe(db: Session):
    """Refresh the dynamic universe from exchange data."""
    try:
        top_coins = get_top_coins_by_volume(
            n=settings.dynamic_universe_size,
            quote=settings.quote_currency,
        )
        if not top_coins:
            logger.warning("Could not fetch top coins - keeping existing universe")
            return

        db.query(Asset).filter(Asset.source == AssetSource.DYNAMIC).update({"is_active": False})

        for rank, symbol in enumerate(top_coins, 1):
            base = symbol.split("/")[0]
            existing = db.query(Asset).filter(Asset.symbol == symbol).first()
            if existing:
                existing.is_active = True
                existing.market_cap_rank = rank
            else:
                asset = Asset(
                    symbol=symbol,
                    base_currency=base,
                    quote_currency=settings.quote_currency,
                    source=AssetSource.DYNAMIC,
                    is_active=True,
                    market_cap_rank=rank,
                )
                db.add(asset)

        db.commit()
        logger.info(f"Updated dynamic universe: {len(top_coins)} coins")

    except Exception as e:
        logger.error(f"Error refreshing universe: {e}")
        db.rollback()


def _evaluate_asset(
    db: Session,
    asset: Asset,
    strategies: List[Strategy],
    current_regime: str,
    scan_log_id: int,
) -> int:
    """Evaluate all strategies against a single asset. Returns count of new setups."""
    setups_created = 0

    timeframes = set()
    for strat in strategies:
        for cond in strat.conditions:
            timeframes.add(cond.timeframe)

    data = fetch_multi_timeframe(asset.symbol, list(timeframes))

    funding_rate = fetch_funding_rate(asset.symbol)
    open_interest = fetch_open_interest(asset.symbol)

    for tf, df in data.items():
        if df is not None:
            df["_funding_rate"] = funding_rate
            df["_open_interest"] = open_interest

    for tf, df in data.items():
        if df is not None:
            data[tf] = add_all_default_indicators(df)

    for strat in strategies:
        all_required_pass, required_met, required_total, bonus_met, bonus_total = (
            _evaluate_strategy_conditions(strat, data)
        )

        direction = strat.direction.value if isinstance(strat.direction, Direction) else str(strat.direction)
        if direction == "both":
            direction = "long"

        existing = db.query(Setup).filter(
            Setup.asset_id == asset.id,
            Setup.strategy_id == strat.id,
            Setup.status.in_([SetupStatus.DETECTED, SetupStatus.ACTIVE]),
        ).first()
        if existing:
            if all_required_pass:
                existing.status = SetupStatus.ACTIVE
                existing.required_conditions_met = required_met
                existing.bonus_conditions_met = bonus_met
                existing.total_conditions = required_total + bonus_total
            elif existing.status == SetupStatus.ACTIVE:
                existing.status = SetupStatus.DETECTED
            continue

        if not all_required_pass:
            continue

        current_price = None
        for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
            if tf in data and data[tf] is not None:
                current_price = float(data[tf].iloc[-1]["close"])
                break
        if current_price is None:
            continue

        entry_tf = strat.conditions[0].timeframe if strat.conditions else "1d"
        entry_df = data.get(entry_tf)
        if entry_df is None:
            entry_df = next((v for v in data.values() if v is not None), None)
        if entry_df is None:
            continue

        levels = calculate_key_levels(entry_df, direction, current_price)

        setup = Setup(
            asset_id=asset.id,
            strategy_id=strat.id,
            direction=Direction(direction),
            status=SetupStatus.DETECTED,
            price_at_detection=current_price,
            funding_rate=funding_rate,
            open_interest=open_interest,
            market_regime=current_regime,
            required_conditions_met=required_met,
            bonus_conditions_met=bonus_met,
            total_conditions=required_total + bonus_total,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=SETUP_EXPIRY_HOURS),
            scan_log_id=scan_log_id,
            **levels,
        )
        db.add(setup)
        setups_created += 1
        logger.info(f"New setup: {asset.symbol} / {strat.name} ({direction})")

    db.commit()
    return setups_created


def _evaluate_strategy_conditions(
    strat: Strategy, data: Dict[str, object]
) -> Tuple[bool, int, int, int, int]:
    """
    Evaluate all conditions for a strategy.
    Returns: (all_required_pass, required_met, required_total, bonus_met, bonus_total).
    """
    required_met = 0
    required_total = 0
    bonus_met = 0
    bonus_total = 0
    all_required_pass = True

    for cond in strat.conditions:
        tf_data = data.get(cond.timeframe)
        if tf_data is None:
            if cond.is_required:
                required_total += 1
                all_required_pass = False
            else:
                bonus_total += 1
            continue

        result = evaluate_condition(cond.condition_type, tf_data, cond.params)

        if cond.is_required:
            required_total += 1
            if result:
                required_met += 1
            else:
                all_required_pass = False
        else:
            bonus_total += 1
            if result:
                bonus_met += 1

    return all_required_pass, required_met, required_total, bonus_met, bonus_total


def _update_setup_lifecycle(db: Session) -> tuple:
    """Update lifecycle of existing setups. Returns (expired_count, invalidated_count)."""
    now = datetime.now(timezone.utc)
    expired = 0
    invalidated = 0

    active_setups = db.query(Setup).filter(
        Setup.status.in_([SetupStatus.DETECTED, SetupStatus.ACTIVE])
    ).all()

    for setup in active_setups:
        if setup.expires_at:
            expires_at = setup.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now >= expires_at:
                setup.status = SetupStatus.EXPIRED
                expired += 1
                continue

        try:
            df = fetch_ohlcv(setup.asset.symbol, "1h", 2)
            if df is not None and len(df) > 0:
                high = float(df.iloc[-1]["high"])
                low = float(df.iloc[-1]["low"])

                if setup.highest_price_after is None or high > setup.highest_price_after:
                    setup.highest_price_after = high
                if setup.lowest_price_after is None or low < setup.lowest_price_after:
                    setup.lowest_price_after = low

                if setup.stop_loss:
                    if setup.direction == Direction.LONG and low <= setup.stop_loss:
                        setup.status = SetupStatus.INVALIDATED
                        setup.invalidated_at = now
                        setup.sl_hit = True
                        setup.sl_hit_at = now
                        invalidated += 1
                        continue
                    if setup.direction == Direction.SHORT and high >= setup.stop_loss:
                        setup.status = SetupStatus.INVALIDATED
                        setup.invalidated_at = now
                        setup.sl_hit = True
                        setup.sl_hit_at = now
                        invalidated += 1
                        continue

                _check_tp_hits(setup, high, low, now)

        except Exception as e:
            logger.error(f"Error updating setup {setup.id}: {e}")

    db.commit()
    return expired, invalidated


def _check_tp_hits(setup: Setup, high: float, low: float, now: datetime):
    """Check if take-profit levels have been hit."""
    if setup.direction == Direction.LONG:
        if setup.take_profit_1 and high >= setup.take_profit_1 and not setup.tp1_hit:
            setup.tp1_hit = True
            setup.tp1_hit_at = now
        if setup.take_profit_2 and high >= setup.take_profit_2 and not setup.tp2_hit:
            setup.tp2_hit = True
            setup.tp2_hit_at = now
        if setup.take_profit_3 and high >= setup.take_profit_3 and not setup.tp3_hit:
            setup.tp3_hit = True
            setup.tp3_hit_at = now
    elif setup.direction == Direction.SHORT:
        if setup.take_profit_1 and low <= setup.take_profit_1 and not setup.tp1_hit:
            setup.tp1_hit = True
            setup.tp1_hit_at = now
        if setup.take_profit_2 and low <= setup.take_profit_2 and not setup.tp2_hit:
            setup.tp2_hit = True
            setup.tp2_hit_at = now
        if setup.take_profit_3 and low <= setup.take_profit_3 and not setup.tp3_hit:
            setup.tp3_hit = True
            setup.tp3_hit_at = now
