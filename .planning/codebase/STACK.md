# Technology Stack

**Analysis Date:** 2026-02-17

## Languages

**Primary:**
- Python 3.x - Backend API, scanner engine, data processing
- JavaScript (ES6+) - Frontend application, client-side logic

**Secondary:**
- HTML/CSS - Frontend UI structure and styling

## Runtime

**Environment:**
- Python 3.x (CPython)
- Modern web browser (ES6+ support)

**Package Manager:**
- pip (Python) - `requirements.txt` present
- No JavaScript package manager detected (vanilla JS frontend)

## Frameworks

**Core:**
- FastAPI 0.115.6 - REST API framework, async web server
- Uvicorn 0.34.0 - ASGI server for FastAPI
- SQLAlchemy 2.0.36 - ORM for database operations
- Alembic 1.14.0 - Database migration tool

**Testing:**
- Not detected - No test framework configured

**Build/Dev:**
- Python-dotenv 1.0.1 - Environment variable management
- APScheduler 3.10.4 - Background task scheduling

## Key Dependencies

**Critical:**
- ccxt 4.4.35 - Cryptocurrency exchange API client (Binance integration)
- pandas 2.2.3 - Data manipulation and analysis for OHLCV data
- pandas-ta 0.3.14b1 - Technical analysis indicators
- numpy 1.26.4 - Numerical computations for indicators
- Pydantic 2.10.3 - Data validation and settings management
- Pydantic-settings 2.7.0 - Settings management from environment

**Infrastructure:**
- httpx 0.28.1 - Async HTTP client
- aiofiles 24.1.0 - Async file operations
- Jinja2 3.1.4 - Template engine (for static file serving)
- python-multipart 0.0.18 - Form data handling

**Frontend:**
- TradingView Lightweight Charts 4.1.3 - Charting library (loaded from CDN)

## Configuration

**Environment:**
- Configured via `.env` file (see `env.example`)
- Pydantic Settings loads from `.env` automatically
- Key configs: `EXCHANGE_ID`, `DATABASE_URL`, `HOST`, `PORT`, `SCAN_INTERVAL_MINUTES`, `DYNAMIC_UNIVERSE_SIZE`
- Optional: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` for notifications

**Build:**
- No build step required for Python backend
- Frontend is static HTML/CSS/JS (no bundler)

## Platform Requirements

**Development:**
- Python 3.x
- pip for package management
- Modern web browser

**Production:**
- Python 3.x runtime
- ASGI-compatible server (Uvicorn)
- SQLite database (default) or PostgreSQL via `DATABASE_URL`
- Exchange API access (Binance by default)

---
*Stack analysis: 2026-02-17*
