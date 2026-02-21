"""
Trade journal endpoints.
"""
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db
from backend.models import JournalEntry, JournalAction, JournalOutcome, Direction, Setup
from backend.schemas import JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse, JournalStats

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("/", response_model=List[JournalEntryResponse])
def list_journal_entries(
    strategy_name: Optional[str] = None,
    tag: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(JournalEntry)
    if strategy_name:
        query = query.filter(JournalEntry.strategy_name == strategy_name)
    if outcome:
        query = query.filter(JournalEntry.outcome == outcome)
    if tag:
        query = query.filter(JournalEntry.tags.contains(f'"{tag}"'))

    entries = query.order_by(JournalEntry.created_at.desc()).limit(limit).all()
    return [_entry_to_response(e) for e in entries]


@router.post("/", response_model=JournalEntryResponse)
def create_journal_entry(data: JournalEntryCreate, db: Session = Depends(get_db)):
    entry = JournalEntry(
        setup_id=data.setup_id,
        asset_symbol=data.asset_symbol,
        strategy_name=data.strategy_name,
        action=JournalAction(data.action),
        outcome=JournalOutcome(data.outcome) if data.outcome else None,
        actual_entry=data.actual_entry,
        actual_stop=data.actual_stop,
        actual_exit=data.actual_exit,
        actual_tp1=data.actual_tp1 if data.actual_tp1 is not None else data.actual_exit,
        actual_tp2=data.actual_tp2,
        actual_tp3=data.actual_tp3,
        position_size=data.position_size,
        pnl_absolute=data.pnl_absolute,
        pnl_r_multiple=data.pnl_r_multiple,
        planned_rr=data.planned_rr,
        notes=data.notes,
    )
    if data.direction:
        entry.direction = Direction(data.direction)
    if data.tags:
        entry.tag_list = data.tags

    # Auto-populate from setup if linked
    if data.setup_id:
        setup = db.query(Setup).filter(Setup.id == data.setup_id).first()
        if setup:
            if not data.asset_symbol:
                entry.asset_symbol = setup.asset.symbol
            if not data.strategy_name:
                entry.strategy_name = setup.strategy.name
            if not data.direction:
                entry.direction = setup.direction

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_to_response(entry)


@router.put("/{entry_id}", response_model=JournalEntryResponse)
def update_journal_entry(entry_id: int, data: JournalEntryUpdate, db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if data.action is not None:
        entry.action = JournalAction(data.action)
    if data.outcome is not None:
        entry.outcome = JournalOutcome(data.outcome)
    if data.actual_entry is not None:
        entry.actual_entry = data.actual_entry
    if data.actual_stop is not None:
        entry.actual_stop = data.actual_stop
    if data.actual_exit is not None:
        entry.actual_exit = data.actual_exit
    if data.actual_tp1 is not None:
        entry.actual_tp1 = data.actual_tp1
    elif data.actual_exit is not None:
        entry.actual_tp1 = data.actual_exit
    if data.actual_tp2 is not None:
        entry.actual_tp2 = data.actual_tp2
    if data.actual_tp3 is not None:
        entry.actual_tp3 = data.actual_tp3
    if data.position_size is not None:
        entry.position_size = data.position_size
    if data.pnl_absolute is not None:
        entry.pnl_absolute = data.pnl_absolute
    if data.pnl_r_multiple is not None:
        entry.pnl_r_multiple = data.pnl_r_multiple
    if data.planned_rr is not None:
        entry.planned_rr = data.planned_rr
    if data.notes is not None:
        entry.notes = data.notes
    if data.tags is not None:
        entry.tag_list = data.tags

    db.commit()
    db.refresh(entry)
    return _entry_to_response(entry)


@router.delete("/{entry_id}")
def delete_journal_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Journal entry deleted"}


@router.get("/stats", response_model=JournalStats)
def get_journal_stats(
    strategy_name: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = db.query(JournalEntry).filter(JournalEntry.created_at >= since)
    if strategy_name:
        query = query.filter(JournalEntry.strategy_name == strategy_name)

    entries = query.all()
    total = len(entries)
    wins = sum(1 for e in entries if e.outcome == JournalOutcome.WIN)
    losses = sum(1 for e in entries if e.outcome == JournalOutcome.LOSS)
    breakevens = sum(1 for e in entries if e.outcome == JournalOutcome.BREAKEVEN)
    open_trades = sum(1 for e in entries if e.outcome == JournalOutcome.OPEN)

    completed = wins + losses
    win_rate = (wins / completed * 100) if completed > 0 else None

    r_multiples = [e.pnl_r_multiple for e in entries if e.pnl_r_multiple is not None]
    avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else None

    total_pnl = sum(e.pnl_absolute for e in entries if e.pnl_absolute is not None) or None

    # Profit factor
    gross_profit = sum(e.pnl_absolute for e in entries if e.pnl_absolute and e.pnl_absolute > 0)
    gross_loss = abs(sum(e.pnl_absolute for e in entries if e.pnl_absolute and e.pnl_absolute < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    return JournalStats(
        total_trades=total,
        wins=wins,
        losses=losses,
        breakevens=breakevens,
        open_trades=open_trades,
        win_rate=round(win_rate, 1) if win_rate else None,
        avg_r_multiple=round(avg_r, 2) if avg_r else None,
        total_pnl=round(total_pnl, 2) if total_pnl else None,
        profit_factor=round(profit_factor, 2) if profit_factor else None,
    )


@router.get("/calendar")
def get_journal_calendar(
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get journal entries grouped by date for calendar heatmap."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    entries = db.query(JournalEntry).filter(JournalEntry.created_at >= since).all()

    calendar = {}
    for entry in entries:
        date_key = entry.created_at.strftime("%Y-%m-%d")
        if date_key not in calendar:
            calendar[date_key] = {"trades": 0, "pnl": 0, "wins": 0, "losses": 0}
        calendar[date_key]["trades"] += 1
        if entry.pnl_absolute:
            calendar[date_key]["pnl"] += entry.pnl_absolute
        if entry.outcome == JournalOutcome.WIN:
            calendar[date_key]["wins"] += 1
        elif entry.outcome == JournalOutcome.LOSS:
            calendar[date_key]["losses"] += 1

    return calendar


def _entry_to_response(entry: JournalEntry) -> JournalEntryResponse:
    tp1 = entry.actual_tp1 if entry.actual_tp1 is not None else entry.actual_exit

    return JournalEntryResponse(
        id=entry.id,
        setup_id=entry.setup_id,
        asset_symbol=entry.asset_symbol,
        strategy_name=entry.strategy_name,
        direction=entry.direction.value if entry.direction else None,
        action=entry.action.value if isinstance(entry.action, JournalAction) else entry.action,
        outcome=entry.outcome.value if isinstance(entry.outcome, JournalOutcome) else entry.outcome,
        actual_entry=entry.actual_entry,
        actual_stop=entry.actual_stop,
        actual_exit=entry.actual_exit,
        actual_tp1=tp1,
        actual_tp2=entry.actual_tp2,
        actual_tp3=entry.actual_tp3,
        position_size=entry.position_size,
        pnl_absolute=entry.pnl_absolute,
        pnl_r_multiple=entry.pnl_r_multiple,
        planned_rr=entry.planned_rr,
        notes=entry.notes,
        tags=entry.tag_list,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )
