"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ─── Asset Schemas ────────────────────────────────────────────────────────────

class AssetBase(BaseModel):
    symbol: str = Field(..., examples=["BTC/USDT"])
    base_currency: str = Field(..., examples=["BTC"])
    quote_currency: str = Field(default="USDT")
    source: str = Field(default="watchlist")

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    is_active: bool
    market_cap_rank: Optional[int] = None
    added_at: datetime
    model_config = {"from_attributes": True}


# ─── Strategy Condition Schemas ───────────────────────────────────────────────

class ConditionBase(BaseModel):
    condition_type: str = Field(..., examples=["price_above_ma"])
    timeframe: str = Field(default="1d", examples=["4h"])
    parameters: dict = Field(default_factory=dict)
    is_required: bool = Field(default=True)
    order: int = Field(default=0)

class ConditionCreate(ConditionBase):
    pass

class ConditionResponse(ConditionBase):
    id: int
    strategy_id: int
    model_config = {"from_attributes": True}


# ─── Strategy Schemas ─────────────────────────────────────────────────────────

class StrategyBase(BaseModel):
    name: str = Field(..., examples=["Trend Pullback Long"])
    description: Optional[str] = None
    direction: str = Field(default="long")
    is_active: bool = Field(default=True)
    valid_regimes: Optional[List[str]] = None

class StrategyCreate(StrategyBase):
    conditions: List[ConditionCreate] = Field(default_factory=list)

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    direction: Optional[str] = None
    is_active: Optional[bool] = None
    valid_regimes: Optional[List[str]] = None
    conditions: Optional[List[ConditionCreate]] = None

class StrategyResponse(StrategyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    conditions: List[ConditionResponse] = []
    recent_setups_count: int = 0
    win_rate: Optional[float] = None
    model_config = {"from_attributes": True}


# ─── Setup Schemas ────────────────────────────────────────────────────────────

class SetupResponse(BaseModel):
    id: int
    asset: AssetResponse
    strategy_name: str
    strategy_id: int
    direction: str
    status: str

    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    price_at_detection: float

    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    market_regime: Optional[str] = None

    required_conditions_met: int = 0
    bonus_conditions_met: int = 0
    total_conditions: int = 0

    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    sl_hit: bool = False

    detected_at: datetime
    expires_at: Optional[datetime] = None
    invalidated_at: Optional[datetime] = None

    tradingview_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Scan Log Schemas ─────────────────────────────────────────────────────────

class ScanLogResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    assets_scanned: int
    setups_found: int
    setups_expired: int = 0
    setups_invalidated: int = 0
    market_regime: Optional[str] = None
    errors: Optional[str] = None
    status: str
    model_config = {"from_attributes": True}


# ─── Journal Schemas ──────────────────────────────────────────────────────────

class JournalEntryCreate(BaseModel):
    setup_id: Optional[int] = None
    asset_symbol: str
    strategy_name: Optional[str] = None
    direction: Optional[str] = None
    action: str = "took_trade"
    outcome: Optional[str] = "open"
    actual_entry: Optional[float] = None
    actual_stop: Optional[float] = None
    actual_exit: Optional[float] = None
    position_size: Optional[float] = None
    pnl_absolute: Optional[float] = None
    pnl_r_multiple: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class JournalEntryUpdate(BaseModel):
    action: Optional[str] = None
    outcome: Optional[str] = None
    actual_entry: Optional[float] = None
    actual_stop: Optional[float] = None
    actual_exit: Optional[float] = None
    position_size: Optional[float] = None
    pnl_absolute: Optional[float] = None
    pnl_r_multiple: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class JournalEntryResponse(BaseModel):
    id: int
    setup_id: Optional[int] = None
    asset_symbol: str
    strategy_name: Optional[str] = None
    direction: Optional[str] = None
    action: str
    outcome: Optional[str] = None
    actual_entry: Optional[float] = None
    actual_stop: Optional[float] = None
    actual_exit: Optional[float] = None
    position_size: Optional[float] = None
    pnl_absolute: Optional[float] = None
    pnl_r_multiple: Optional[float] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class JournalStats(BaseModel):
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakevens: int = 0
    open_trades: int = 0
    win_rate: Optional[float] = None
    avg_r_multiple: Optional[float] = None
    total_pnl: Optional[float] = None
    profit_factor: Optional[float] = None


# ─── Backtester Schemas ──────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    strategy_id: int
    symbols: Optional[List[str]] = None  # None = use full universe
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    timeframe: str = "1d"

class BacktestResult(BaseModel):
    strategy_name: str
    symbols_tested: int
    total_setups: int
    wins: int
    losses: int
    win_rate: float
    avg_rr: float
    max_drawdown: float
    setups_per_month: float
    equity_curve: List[float] = []
    setup_details: List[dict] = []


# ─── Misc ─────────────────────────────────────────────────────────────────────

class ScanTriggerResponse(BaseModel):
    message: str
    scan_id: Optional[int] = None


class ScanStatusResponse(BaseModel):
    is_running: bool
    message: str
    scan_id: Optional[int] = None


class ConditionTypeInfo(BaseModel):
    type: str
    category: str
    description: str
    parameters: dict
    default_timeframe: str

class MarketRegimeResponse(BaseModel):
    regime: str
    description: str
    btc_trend: str
    confidence: float
    indicators: dict

class DashboardStats(BaseModel):
    active_setups: int
    active_strategies: int
    assets_in_universe: int
    last_scan: Optional[ScanLogResponse] = None
    setups_today: int
    market_regime: Optional[MarketRegimeResponse] = None

class WebhookAlert(BaseModel):
    """TradingView webhook incoming alert."""
    symbol: Optional[str] = None
    action: Optional[str] = None
    price: Optional[float] = None
    message: Optional[str] = None
    timeframe: Optional[str] = None
    strategy: Optional[str] = None