# Architecture

**Analysis Date:** 2026-02-17

## Pattern Overview

**Overall:** Layered architecture with clear separation between API, business logic, and data access

**Key Characteristics:**
- FastAPI REST API layer with router-based organization
- Service layer for background tasks and external integrations
- Scanner engine with modular condition evaluation
- SQLAlchemy ORM for data persistence
- Static frontend with vanilla JavaScript

## Layers

**API Layer:**
- Purpose: HTTP request handling, validation, response formatting
- Location: `backend/routers/`
- Contains: FastAPI router modules (dashboard, assets, strategies, setups, scans, journal, backtester, webhooks, chart_data)
- Depends on: Database sessions, models, schemas, services
- Used by: Frontend JavaScript client (`frontend/js/api.js`)

**Business Logic Layer:**
- Purpose: Core trading scanner logic, condition evaluation, indicator calculations
- Location: `backend/scanner/`
- Contains: Engine (`engine.py`), conditions (`conditions.py`), indicators (`indicators.py`), data fetcher (`data_fetcher.py`), regime detection (`regime.py`), level calculation (`levels.py`), backtester (`backtester.py`)
- Depends on: Exchange API (ccxt), pandas for data processing
- Used by: API routers, scheduler

**Data Access Layer:**
- Purpose: Database models, session management, schema definitions
- Location: `backend/models.py`, `backend/database.py`, `backend/schemas.py`
- Contains: SQLAlchemy models, Pydantic schemas, database initialization
- Depends on: SQLAlchemy, database engine
- Used by: All routers and services

**Service Layer:**
- Purpose: Background tasks, external integrations, cross-cutting concerns
- Location: `backend/services/`
- Contains: Scheduler (`scheduler.py`), log streaming (`log_streamer.py`), Telegram notifications (`telegram.py`)
- Depends on: Scanner engine, database, external APIs
- Used by: Application lifecycle (startup/shutdown)

**Frontend Layer:**
- Purpose: User interface, data visualization, user interactions
- Location: `frontend/`
- Contains: HTML (`index.html`), CSS (`css/styles.css`), JavaScript (`js/app.js`, `js/api.js`, `js/utils.js`)
- Depends on: Backend API, TradingView charts library
- Used by: End users

## Data Flow

**Scan Cycle Flow:**

1. Scheduler triggers scan (APScheduler) → `backend/services/scheduler.py`
2. Scanner engine orchestrates scan → `backend/scanner/engine.py`
3. Refresh dynamic universe (fetch top coins from exchange) → `backend/scanner/data_fetcher.py`
4. Detect market regime (BTC analysis) → `backend/scanner/regime.py`
5. For each asset:
   - Fetch multi-timeframe OHLCV data → `backend/scanner/data_fetcher.py`
   - Add technical indicators → `backend/scanner/indicators.py`
   - Evaluate strategies against conditions → `backend/scanner/conditions.py`
   - Calculate key levels (entry, SL, TP) → `backend/scanner/levels.py`
   - Create Setup records if conditions met → `backend/models.py`
6. Update lifecycle of existing setups (expiry, invalidation)
7. Store results in database → SQLAlchemy models

**API Request Flow:**

1. Frontend makes HTTP request → `frontend/js/api.js`
2. FastAPI router receives request → `backend/routers/*.py`
3. Router validates request with Pydantic schema → `backend/schemas.py`
4. Router queries database via SQLAlchemy → `backend/database.py`
5. Router returns Pydantic response model
6. Frontend renders data → `frontend/js/app.js`

**State Management:**
- Server-side: SQLAlchemy models in SQLite database
- Client-side: Vanilla JavaScript variables, no state management framework
- Real-time: WebSocket connection for log streaming (`/ws/logs`)

## Key Abstractions

**Strategy Pattern:**
- Purpose: Composable trading strategies with multiple conditions
- Examples: `backend/models.py` (Strategy, StrategyCondition), `backend/scanner/conditions.py` (evaluate_condition)
- Pattern: Strategy contains multiple conditions, each condition has type, timeframe, parameters

**Repository Pattern (implicit):**
- Purpose: Data access abstraction via SQLAlchemy ORM
- Examples: `backend/database.py` (SessionLocal, get_db), `backend/models.py` (Base models)
- Pattern: Routers use dependency injection for database sessions

**Service Pattern:**
- Purpose: Encapsulate business logic and external integrations
- Examples: `backend/services/scheduler.py`, `backend/services/telegram.py`
- Pattern: Services handle background tasks and cross-cutting concerns

## Entry Points

**Application Entry:**
- Location: `run.py`
- Triggers: Command line execution (`python run.py`)
- Responsibilities: Start Uvicorn ASGI server, load FastAPI app

**FastAPI Application:**
- Location: `backend/main.py`
- Triggers: Uvicorn server startup
- Responsibilities: Register routers, mount static files, setup WebSocket endpoints, lifecycle management (scheduler start/stop)

**Scheduled Tasks:**
- Location: `backend/services/scheduler.py`
- Triggers: APScheduler interval trigger (configurable via `SCAN_INTERVAL_MINUTES`)
- Responsibilities: Execute periodic scans in background thread

## Error Handling

**Strategy:** Try-except blocks with logging, graceful degradation

**Patterns:**
- API errors return HTTP status codes with error messages
- Scanner errors are logged and collected in `ScanLog.errors` JSON field
- Data fetch failures return `None`, calling code handles gracefully
- WebSocket errors handled via connection lifecycle (onclose, onerror)

## Cross-Cutting Concerns

**Logging:** Python `logging` module, INFO level by default, WebSocket streaming to frontend

**Validation:** Pydantic models for request/response validation (`backend/schemas.py`)

**Authentication:** None - No authentication implemented

---
*Architecture analysis: 2026-02-17*
