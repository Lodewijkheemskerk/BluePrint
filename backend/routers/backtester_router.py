"""
Backtester endpoints.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Strategy, Asset
from backend.schemas import BacktestRequest, BacktestResult
from backend.scanner.backtester import backtest_strategy

router = APIRouter(prefix="/api/backtest", tags=["backtester"])


@router.post("/run", response_model=BacktestResult)
def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    strat = db.query(Strategy).filter(Strategy.id == req.strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Get symbols to test
    if req.symbols:
        symbols = req.symbols
    else:
        assets = db.query(Asset).filter(Asset.is_active == True).limit(20).all()
        symbols = [a.symbol for a in assets]

    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols to test")

    # Build conditions list from strategy
    conditions = []
    for cond in strat.conditions:
        conditions.append({
            "condition_type": cond.condition_type,
            "timeframe": cond.timeframe,
            "parameters": cond.params,
            "is_required": cond.is_required,
        })

    direction = strat.direction.value if hasattr(strat.direction, 'value') else strat.direction

    result = backtest_strategy(
        strategy_conditions=conditions,
        direction=direction,
        symbols=symbols,
        timeframe=req.timeframe,
    )
    result["strategy_name"] = strat.name

    return BacktestResult(**result)
