# External Integrations

**Analysis Date:** 2026-02-17

## APIs & External Services

**Cryptocurrency Exchange:**
- Binance (default, configurable via `EXCHANGE_ID`) - Market data, OHLCV, tickers, funding rates, open interest
  - SDK/Client: `ccxt` library (`backend/scanner/data_fetcher.py`)
  - Auth: None required for public data endpoints
  - Spot market: OHLCV data, ticker data
  - Futures market: Funding rates, open interest (optional)

**Charting:**
- TradingView Lightweight Charts - Client-side charting library
  - Loaded from CDN: `https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js`
  - Used in: `frontend/js/app.js` for setup detail charts

## Data Storage

**Databases:**
- SQLite (default)
  - Connection: `sqlite:///./blueprint.db` (configurable via `DATABASE_URL`)
  - Client: SQLAlchemy ORM (`backend/database.py`)
  - Schema: Managed via SQLAlchemy models (`backend/models.py`)

**File Storage:**
- Local filesystem only - Static frontend files served by FastAPI

**Caching:**
- None - No caching layer implemented

## Authentication & Identity

**Auth Provider:**
- None - No authentication required (local/development tool)

**Implementation:**
- No auth middleware or user management

## Monitoring & Observability

**Error Tracking:**
- None - Standard Python logging only

**Logs:**
- Python `logging` module with INFO level
- WebSocket log streaming to frontend (`backend/services/log_streamer.py`)
- Log format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Frontend log viewer with filtering and search (`frontend/js/app.js`)

## CI/CD & Deployment

**Hosting:**
- Not specified - Local development setup

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- `EXCHANGE_ID` - Exchange identifier (default: "binance")
- `DATABASE_URL` - Database connection string (default: "sqlite:///./blueprint.db")
- `HOST` - Server host (default: "127.0.0.1")
- `PORT` - Server port (default: 8000)
- `SCAN_INTERVAL_MINUTES` - Scan frequency (default: 240)
- `DYNAMIC_UNIVERSE_SIZE` - Number of top coins to scan (default: 100)
- `QUOTE_CURRENCY` - Quote currency for pairs (default: "USDT")

**Optional env vars:**
- `TELEGRAM_BOT_TOKEN` - Telegram bot token for notifications
- `TELEGRAM_CHAT_ID` - Telegram chat ID for notifications

**Secrets location:**
- `.env` file (not committed, see `env.example`)

## Webhooks & Callbacks

**Incoming:**
- `/api/webhooks/tradingview` - TradingView webhook endpoint (`backend/routers/webhooks.py`)
  - Accepts POST requests with alert data
  - Optional integration for external alerts

**Outgoing:**
- Telegram notifications (optional) - Via `backend/services/telegram.py`
  - Sends setup alerts when configured

---
*Integration audit: 2026-02-17*
