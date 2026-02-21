"""
APScheduler setup for periodic scanning.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from backend.config import settings
from backend.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _run_scheduled_scan():
    """Execute a scan in a background thread with its own DB session."""
    from backend.scanner.engine import run_scan
    logger.info("Starting scheduled scan...")
    db = SessionLocal()
    try:
        scan_log = run_scan(db)
        logger.info(f"Scheduled scan completed: {scan_log.setups_found} setups found")
    except Exception as e:
        logger.error(f"Scheduled scan failed: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler."""
    interval_minutes = settings.scan_interval_minutes
    scheduler.add_job(
        _run_scheduled_scan,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="scan_cycle",
        name=f"Scan every {interval_minutes} minutes",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — scanning every {interval_minutes} minutes")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
