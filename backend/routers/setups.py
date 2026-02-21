"""
Setup alert endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from backend.database import get_db
from backend.models import Setup, SetupStatus, Direction
from backend.schemas import SetupResponse

router = APIRouter(prefix="/api/setups", tags=["setups"])


def _setup_to_response(setup: Setup) -> SetupResponse:
    symbol = setup.asset.symbol.replace("/", "")
    tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"

    return SetupResponse(
        id=setup.id,
        asset=setup.asset,
        strategy_name=setup.strategy.name,
        strategy_id=setup.strategy_id,
        direction=setup.direction.value if isinstance(setup.direction, Direction) else setup.direction,
        status=setup.status.value if isinstance(setup.status, SetupStatus) else setup.status,
        entry_price=setup.entry_price,
        stop_loss=setup.stop_loss,
        take_profit_1=setup.take_profit_1,
        take_profit_2=setup.take_profit_2,
        take_profit_3=setup.take_profit_3,
        risk_reward_ratio=setup.risk_reward_ratio,
        price_at_detection=setup.price_at_detection,
        funding_rate=setup.funding_rate,
        open_interest=setup.open_interest,
        market_regime=setup.market_regime,
        required_conditions_met=setup.required_conditions_met,
        bonus_conditions_met=setup.bonus_conditions_met,
        total_conditions=setup.total_conditions,
        tp1_hit=setup.tp1_hit,
        tp2_hit=setup.tp2_hit,
        tp3_hit=setup.tp3_hit,
        sl_hit=setup.sl_hit,
        detected_at=setup.detected_at,
        expires_at=setup.expires_at,
        invalidated_at=setup.invalidated_at,
        tradingview_url=tv_url,
    )


@router.get("/", response_model=List[SetupResponse])
def list_setups(
    status: Optional[str] = None,
    direction: Optional[str] = None,
    strategy_id: Optional[int] = None,
    asset_symbol: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Setup).options(
        joinedload(Setup.asset),
        joinedload(Setup.strategy),
    )

    if status:
        query = query.filter(Setup.status == status)
    else:
        query = query.filter(Setup.status.in_([SetupStatus.DETECTED, SetupStatus.ACTIVE]))

    if direction:
        query = query.filter(Setup.direction == direction)
    if strategy_id:
        query = query.filter(Setup.strategy_id == strategy_id)
    if asset_symbol:
        query = query.join(Setup.asset).filter(Setup.asset.has(symbol=asset_symbol))

    setups = query.order_by(Setup.detected_at.desc()).limit(limit).all()
    return [_setup_to_response(s) for s in setups]


@router.get("/all", response_model=List[SetupResponse])
def list_all_setups(limit: int = Query(default=100, le=500), db: Session = Depends(get_db)):
    setups = db.query(Setup).options(
        joinedload(Setup.asset),
        joinedload(Setup.strategy),
    ).order_by(Setup.detected_at.desc()).limit(limit).all()
    return [_setup_to_response(s) for s in setups]


@router.get("/{setup_id}", response_model=SetupResponse)
def get_setup(setup_id: int, db: Session = Depends(get_db)):
    setup = db.query(Setup).options(
        joinedload(Setup.asset),
        joinedload(Setup.strategy),
    ).filter(Setup.id == setup_id).first()
    if not setup:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Setup not found")
    return _setup_to_response(setup)


@router.get("/by-asset/{symbol}", response_model=List[SetupResponse])
def get_setups_by_asset(symbol: str, limit: int = 20, db: Session = Depends(get_db)):
    setups = db.query(Setup).options(
        joinedload(Setup.asset),
        joinedload(Setup.strategy),
    ).join(Setup.asset).filter(
        Setup.asset.has(symbol=symbol)
    ).order_by(Setup.detected_at.desc()).limit(limit).all()
    return [_setup_to_response(s) for s in setups]


@router.get("/performance/summary")
def get_performance_summary(strategy_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get performance summary across all setups or for a specific strategy."""
    query = db.query(Setup)
    if strategy_id:
        query = query.filter(Setup.strategy_id == strategy_id)

    total = query.count()
    active = query.filter(Setup.status.in_([SetupStatus.DETECTED, SetupStatus.ACTIVE])).count()
    expired = query.filter(Setup.status == SetupStatus.EXPIRED).count()
    invalidated = query.filter(Setup.status == SetupStatus.INVALIDATED).count()
    tp1_wins = query.filter(Setup.tp1_hit == True).count()
    tp2_wins = query.filter(Setup.tp2_hit == True).count()
    tp3_wins = query.filter(Setup.tp3_hit == True).count()
    sl_losses = query.filter(Setup.sl_hit == True).count()

    completed = tp1_wins + sl_losses
    win_rate = (tp1_wins / completed * 100) if completed > 0 else None

    return {
        "total_setups": total,
        "active": active,
        "expired": expired,
        "invalidated": invalidated,
        "tp1_hits": tp1_wins,
        "tp2_hits": tp2_wins,
        "tp3_hits": tp3_wins,
        "sl_hits": sl_losses,
        "win_rate": round(win_rate, 1) if win_rate else None,
    }
