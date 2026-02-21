"""
SQLAlchemy database models for BluePrint.
"""
import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey,
    Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class Direction(str, enum.Enum):
    LONG = "long"
    SHORT = "short"
    BOTH = "both"


class SetupStatus(str, enum.Enum):
    DETECTED = "detected"
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class AssetSource(str, enum.Enum):
    DYNAMIC = "dynamic"
    WATCHLIST = "watchlist"


class MarketRegimeType(str, enum.Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"


class JournalAction(str, enum.Enum):
    TOOK_TRADE = "took_trade"
    SKIPPED = "skipped"
    PARTIAL = "partial"


class JournalOutcome(str, enum.Enum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    OPEN = "open"


# ─── Models ───────────────────────────────────────────────────────────────────

class Asset(Base):
    """A crypto asset in the scanning universe."""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(30), unique=True, nullable=False, index=True)
    base_currency = Column(String(15), nullable=False)
    quote_currency = Column(String(15), nullable=False, default="USDT")
    source = Column(SAEnum(AssetSource), nullable=False, default=AssetSource.DYNAMIC)
    is_active = Column(Boolean, default=True)
    market_cap_rank = Column(Integer, nullable=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    setups = relationship("Setup", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Asset {self.symbol}>"


class Strategy(Base):
    """A named trading strategy composed of multiple conditions."""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    direction = Column(SAEnum(Direction), nullable=False, default=Direction.LONG)
    is_active = Column(Boolean, default=True)
    # Market regime filter – JSON list e.g. ["trending_up", "ranging"] or null for any
    valid_regimes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    conditions = relationship("StrategyCondition", back_populates="strategy",
                              cascade="all, delete-orphan", order_by="StrategyCondition.order")
    setups = relationship("Setup", back_populates="strategy", cascade="all, delete-orphan")

    @property
    def regime_list(self):
        if not self.valid_regimes:
            return None
        return json.loads(self.valid_regimes)

    @regime_list.setter
    def regime_list(self, value):
        self.valid_regimes = json.dumps(value) if value else None

    def __repr__(self):
        return f"<Strategy {self.name}>"


class StrategyCondition(Base):
    """An individual condition within a strategy."""
    __tablename__ = "strategy_conditions"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    condition_type = Column(String(60), nullable=False)
    timeframe = Column(String(10), nullable=False, default="1d")
    parameters = Column(Text, nullable=False, default="{}")
    is_required = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    strategy = relationship("Strategy", back_populates="conditions")

    @property
    def params(self) -> dict:
        return json.loads(self.parameters) if self.parameters else {}

    @params.setter
    def params(self, value: dict):
        self.parameters = json.dumps(value)

    def __repr__(self):
        return f"<Condition {self.condition_type} on {self.timeframe}>"


class Setup(Base):
    """A detected trade setup — the main output of the scanner."""
    __tablename__ = "setups"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    direction = Column(SAEnum(Direction), nullable=False)
    status = Column(SAEnum(SetupStatus), nullable=False, default=SetupStatus.DETECTED)

    # Price levels
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit_1 = Column(Float, nullable=True)
    take_profit_2 = Column(Float, nullable=True)
    take_profit_3 = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    price_at_detection = Column(Float, nullable=False)

    # Funding rate snapshot at detection time
    funding_rate = Column(Float, nullable=True)
    open_interest = Column(Float, nullable=True)

    # Market regime at detection time
    market_regime = Column(String(30), nullable=True)

    # Confidence
    required_conditions_met = Column(Integer, default=0)
    bonus_conditions_met = Column(Integer, default=0)
    total_conditions = Column(Integer, default=0)

    # Timestamps
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    invalidated_at = Column(DateTime, nullable=True)

    # Performance tracking
    tp1_hit = Column(Boolean, default=False)
    tp2_hit = Column(Boolean, default=False)
    tp3_hit = Column(Boolean, default=False)
    sl_hit = Column(Boolean, default=False)
    tp1_hit_at = Column(DateTime, nullable=True)
    tp2_hit_at = Column(DateTime, nullable=True)
    tp3_hit_at = Column(DateTime, nullable=True)
    sl_hit_at = Column(DateTime, nullable=True)
    highest_price_after = Column(Float, nullable=True)
    lowest_price_after = Column(Float, nullable=True)

    scan_log_id = Column(Integer, ForeignKey("scan_logs.id"), nullable=True)

    asset = relationship("Asset", back_populates="setups")
    strategy = relationship("Strategy", back_populates="setups")
    journal_entry = relationship("JournalEntry", back_populates="setup", uselist=False)

    __table_args__ = (
        Index("ix_setups_status", "status"),
        Index("ix_setups_detected", "detected_at"),
    )

    def __repr__(self):
        return f"<Setup {self.asset_id}/{self.strategy_id} ({self.status})>"


class ScanLog(Base):
    """Log entry for each scan cycle."""
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    assets_scanned = Column(Integer, default=0)
    setups_found = Column(Integer, default=0)
    setups_expired = Column(Integer, default=0)
    setups_invalidated = Column(Integer, default=0)
    market_regime = Column(String(30), nullable=True)
    errors = Column(Text, nullable=True)
    status = Column(String(20), default="running")

    setups = relationship("Setup", backref="scan_log")

    def __repr__(self):
        return f"<ScanLog {self.id} ({self.status})>"


class JournalEntry(Base):
    """A trade journal entry linked to a setup."""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    setup_id = Column(Integer, ForeignKey("setups.id"), nullable=True)
    asset_symbol = Column(String(30), nullable=False)
    strategy_name = Column(String(100), nullable=True)
    direction = Column(SAEnum(Direction), nullable=True)

    action = Column(SAEnum(JournalAction), nullable=False, default=JournalAction.TOOK_TRADE)
    outcome = Column(SAEnum(JournalOutcome), nullable=True, default=JournalOutcome.OPEN)

    # Trade details
    actual_entry = Column(Float, nullable=True)
    actual_stop = Column(Float, nullable=True)
    actual_exit = Column(Float, nullable=True)
    actual_tp1 = Column(Float, nullable=True)
    actual_tp2 = Column(Float, nullable=True)
    actual_tp3 = Column(Float, nullable=True)
    position_size = Column(Float, nullable=True)
    pnl_absolute = Column(Float, nullable=True)
    pnl_r_multiple = Column(Float, nullable=True)
    planned_rr = Column(Float, nullable=True)

    # Notes and tags
    notes = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON list of tag strings

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    setup = relationship("Setup", back_populates="journal_entry")

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return json.loads(self.tags)

    @tag_list.setter
    def tag_list(self, value):
        self.tags = json.dumps(value) if value else None

    __table_args__ = (
        Index("ix_journal_created", "created_at"),
    )

    def __repr__(self):
        return f"<JournalEntry {self.id} {self.asset_symbol}>"
