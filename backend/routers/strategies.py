"""
Strategy CRUD endpoints.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import Strategy, StrategyCondition, Setup, SetupStatus, Direction
from backend.schemas import (
    StrategyCreate, StrategyUpdate, StrategyResponse, ConditionResponse,
    ConditionTypeInfo
)
from backend.scanner.conditions import get_condition_types

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/", response_model=List[StrategyResponse])
def list_strategies(active_only: bool = Query(default=False), db: Session = Depends(get_db)):
    query = db.query(Strategy)
    if active_only:
        query = query.filter(Strategy.is_active == True)
    strategies = query.order_by(Strategy.created_at.desc()).all()
    result = []
    for strat in strategies:
        # Count recent setups
        recent_count = db.query(Setup).filter(
            Setup.strategy_id == strat.id,
            Setup.status.in_([SetupStatus.DETECTED, SetupStatus.ACTIVE]),
        ).count()

        # Calculate win rate from completed setups
        total_completed = db.query(Setup).filter(
            Setup.strategy_id == strat.id,
            Setup.status.in_([SetupStatus.EXPIRED, SetupStatus.INVALIDATED]),
        ).count()
        wins = db.query(Setup).filter(
            Setup.strategy_id == strat.id,
            Setup.status.in_([SetupStatus.EXPIRED, SetupStatus.INVALIDATED]),
            Setup.tp1_hit == True,
        ).count()
        win_rate = (wins / total_completed * 100) if total_completed > 0 else None

        resp = StrategyResponse(
            id=strat.id,
            name=strat.name,
            description=strat.description,
            direction=strat.direction.value if isinstance(strat.direction, Direction) else strat.direction,
            is_active=strat.is_active,
            valid_regimes=strat.regime_list,
            created_at=strat.created_at,
            updated_at=strat.updated_at,
            conditions=[ConditionResponse(
                id=c.id,
                strategy_id=c.strategy_id,
                condition_type=c.condition_type,
                timeframe=c.timeframe,
                parameters=c.params,
                is_required=c.is_required,
                order=c.order,
            ) for c in strat.conditions],
            recent_setups_count=recent_count,
            win_rate=round(win_rate, 1) if win_rate is not None else None,
        )
        result.append(resp)
    return result


@router.post("/", response_model=StrategyResponse)
def create_strategy(data: StrategyCreate, db: Session = Depends(get_db)):
    strat = Strategy(
        name=data.name,
        description=data.description,
        direction=Direction(data.direction),
        is_active=data.is_active,
    )
    if data.valid_regimes:
        strat.regime_list = data.valid_regimes

    for cond_data in data.conditions:
        cond = StrategyCondition(
            condition_type=cond_data.condition_type,
            timeframe=cond_data.timeframe,
            parameters=json.dumps(cond_data.parameters),
            is_required=cond_data.is_required,
            order=cond_data.order,
        )
        strat.conditions.append(cond)

    db.add(strat)
    db.commit()
    db.refresh(strat)

    return StrategyResponse(
        id=strat.id,
        name=strat.name,
        description=strat.description,
        direction=strat.direction.value,
        is_active=strat.is_active,
        valid_regimes=strat.regime_list,
        created_at=strat.created_at,
        updated_at=strat.updated_at,
        conditions=[ConditionResponse(
            id=c.id, strategy_id=c.strategy_id, condition_type=c.condition_type,
            timeframe=c.timeframe, parameters=c.params, is_required=c.is_required, order=c.order,
        ) for c in strat.conditions],
        recent_setups_count=0,
        win_rate=None,
    )


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(strategy_id: int, data: StrategyUpdate, db: Session = Depends(get_db)):
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if data.name is not None:
        strat.name = data.name
    if data.description is not None:
        strat.description = data.description
    if data.direction is not None:
        strat.direction = Direction(data.direction)
    if data.is_active is not None:
        strat.is_active = data.is_active
    if data.valid_regimes is not None:
        strat.regime_list = data.valid_regimes

    if data.conditions is not None:
        # Replace all conditions
        for old_cond in strat.conditions:
            db.delete(old_cond)
        strat.conditions = []
        for cond_data in data.conditions:
            cond = StrategyCondition(
                condition_type=cond_data.condition_type,
                timeframe=cond_data.timeframe,
                parameters=json.dumps(cond_data.parameters),
                is_required=cond_data.is_required,
                order=cond_data.order,
            )
            strat.conditions.append(cond)

    db.commit()
    db.refresh(strat)
    return _strategy_to_response(strat, db)


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    db.delete(strat)
    db.commit()
    return {"message": f"Strategy '{strat.name}' deleted"}


@router.post("/{strategy_id}/toggle")
def toggle_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strat = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strat.is_active = not strat.is_active
    db.commit()
    return {"message": f"Strategy '{strat.name}' is now {'active' if strat.is_active else 'inactive'}"}


@router.get("/condition-types", response_model=List[ConditionTypeInfo])
def list_condition_types():
    return [ConditionTypeInfo(**ct) for ct in get_condition_types()]


def _strategy_to_response(strat: Strategy, db: Session) -> StrategyResponse:
    recent_count = db.query(Setup).filter(
        Setup.strategy_id == strat.id,
        Setup.status.in_([SetupStatus.DETECTED, SetupStatus.ACTIVE]),
    ).count()
    return StrategyResponse(
        id=strat.id,
        name=strat.name,
        description=strat.description,
        direction=strat.direction.value if isinstance(strat.direction, Direction) else strat.direction,
        is_active=strat.is_active,
        valid_regimes=strat.regime_list,
        created_at=strat.created_at,
        updated_at=strat.updated_at,
        conditions=[ConditionResponse(
            id=c.id, strategy_id=c.strategy_id, condition_type=c.condition_type,
            timeframe=c.timeframe, parameters=c.params, is_required=c.is_required, order=c.order,
        ) for c in strat.conditions],
        recent_setups_count=recent_count,
        win_rate=None,
    )
