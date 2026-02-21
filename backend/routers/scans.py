"""
Scan trigger and log endpoints.
"""
import asyncio
import threading
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db, SessionLocal
from backend.models import ScanLog
from backend.schemas import ScanLogResponse, ScanTriggerResponse, ScanStatusResponse
from backend.scanner.engine import cancel_scan, is_scan_running, get_current_scan_id

router = APIRouter(prefix="/api/scans", tags=["scans"])


def _reconcile_stale_scan_logs(db: Session) -> None:
    """
    Finalize stale running scan logs left behind after crashes/restarts.

    Only reconcile when there is no active in-memory scan.
    """
    if is_scan_running():
        return

    stale_logs = db.query(ScanLog).filter(
        ScanLog.status == "running",
        ScanLog.finished_at.is_(None),
    ).all()

    if not stale_logs:
        return

    now = datetime.now(timezone.utc)
    for log in stale_logs:
        log.status = "failed"
        log.finished_at = now
        if not log.errors:
            log.errors = '["Recovered stale running scan after restart"]'
    db.commit()


@router.post("/trigger", response_model=ScanTriggerResponse)
def trigger_scan(db: Session = Depends(get_db)):
    """Trigger a manual scan cycle in a background thread."""
    # Create scan log FIRST, before starting background thread
    scan_log = ScanLog(started_at=datetime.now(timezone.utc), status="running")
    db.add(scan_log)
    db.commit()
    db.refresh(scan_log)
    scan_id = scan_log.id
    
    def _run():
        from backend.scanner.engine import run_scan
        session = SessionLocal()
        try:
            # Pass scan_id to update existing log instead of creating new one
            run_scan(session, scan_id=scan_id)
        finally:
            session.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return ScanTriggerResponse(
        message="Scan triggered — running in background",
        scan_id=scan_id,
    )


@router.get("/logs", response_model=List[ScanLogResponse])
def list_scan_logs(limit: int = 20, db: Session = Depends(get_db)):
    _reconcile_stale_scan_logs(db)
    logs = db.query(ScanLog).order_by(ScanLog.id.desc()).limit(limit).all()
    return [ScanLogResponse.model_validate(log) for log in logs]


@router.get("/logs/{log_id}", response_model=ScanLogResponse)
def get_scan_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(ScanLog).filter(ScanLog.id == log_id).first()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scan log not found")
    return ScanLogResponse.model_validate(log)


@router.post("/stop", response_model=ScanStatusResponse)
def stop_scan():
    """Stop the currently running scan."""
    cancelled = cancel_scan()
    if cancelled:
        return ScanStatusResponse(
            is_running=True,
            message="Scan cancellation requested — it will stop after completing the current asset",
            scan_id=get_current_scan_id()
        )
    else:
        return ScanStatusResponse(
            is_running=False,
            message="No scan is currently running",
            scan_id=None
        )


@router.get("/status", response_model=ScanStatusResponse)
def get_scan_status(db: Session = Depends(get_db)):
    """Get the current scan status."""
    _reconcile_stale_scan_logs(db)
    running = is_scan_running()
    return ScanStatusResponse(
        is_running=running,
        message="Scan is running" if running else "No scan is running",
        scan_id=get_current_scan_id() if running else None
    )
