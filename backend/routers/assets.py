"""
Asset / Universe management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import Asset, AssetSource
from backend.schemas import AssetCreate, AssetResponse

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/", response_model=List[AssetResponse])
def list_assets(active_only: bool = True, source: str = None, db: Session = Depends(get_db)):
    query = db.query(Asset)
    if active_only:
        query = query.filter(Asset.is_active == True)
    if source:
        query = query.filter(Asset.source == source)
    return query.order_by(Asset.market_cap_rank.asc().nullslast(), Asset.symbol).all()


@router.post("/", response_model=AssetResponse)
def add_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    existing = db.query(Asset).filter(Asset.symbol == asset.symbol).first()
    if existing:
        existing.is_active = True
        if asset.source == "watchlist":
            existing.source = AssetSource.WATCHLIST
        db.commit()
        db.refresh(existing)
        return existing

    db_asset = Asset(
        symbol=asset.symbol,
        base_currency=asset.base_currency,
        quote_currency=asset.quote_currency,
        source=AssetSource(asset.source),
        is_active=True,
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


@router.delete("/{asset_id}")
def remove_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.is_active = False
    db.commit()
    return {"message": f"Asset {asset.symbol} deactivated"}


@router.post("/{asset_id}/activate")
def activate_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.is_active = True
    db.commit()
    return {"message": f"Asset {asset.symbol} activated"}
