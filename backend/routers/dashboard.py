"""
Dashboard stats and overview endpoints.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Setup, Strategy, Asset, ScanLog, SetupStatus
from backend.schemas import DashboardStats, ScanLogResponse, MarketRegimeResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    active_setups = db.query(Setup).filter(
        Setup.status.in_([SetupStatus.DETECTED, SetupStatus.ACTIVE])
    ).count()

    active_strategies = db.query(Strategy).filter(Strategy.is_active == True).count()
    assets_count = db.query(Asset).filter(Asset.is_active == True).count()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    setups_today = db.query(Setup).filter(Setup.detected_at >= today_start).count()

    last_scan = db.query(ScanLog).order_by(ScanLog.id.desc()).first()
    last_scan_data = None
    regime_data = None

    if last_scan:
        last_scan_data = ScanLogResponse.model_validate(last_scan)
        if last_scan.market_regime:
            regime_data = MarketRegimeResponse(
                regime=last_scan.market_regime,
                description=f"Detected during last scan",
                btc_trend=last_scan.market_regime.replace("_", " "),
                confidence=0.75,
                indicators={},
            )

    return DashboardStats(
        active_setups=active_setups,
        active_strategies=active_strategies,
        assets_in_universe=assets_count,
        last_scan=last_scan_data,
        setups_today=setups_today,
        market_regime=regime_data,
    )
