# Codebase Structure

**Analysis Date:** 2026-02-17

## Directory Layout

```
[project-root]/
├── backend/              # Python FastAPI backend
│   ├── routers/         # API route handlers
│   ├── scanner/         # Trading scanner engine
│   ├── services/        # Background services
│   ├── __init__.py
│   ├── config.py        # Settings and configuration
│   ├── database.py      # Database setup and session management
│   ├── main.py          # FastAPI application entry
│   ├── models.py        # SQLAlchemy database models
│   └── schemas.py       # Pydantic request/response schemas
├── frontend/            # Static frontend files
│   ├── css/
│   │   └── styles.css   # Application styles
│   ├── js/
│   │   ├── api.js       # API client functions
│   │   ├── app.js       # Main application logic
│   │   ├── utils.js     # Utility functions
│   │   └── components/  # Component modules (if any)
│   └── index.html       # Main HTML page
├── .claude/             # Claude Code configuration
├── .planning/           # GSD planning files
│   └── codebase/        # Codebase mapping documents
├── blueprint.db         # SQLite database file
├── env.example          # Environment variables template
├── requirements.txt     # Python dependencies
├── run.py               # Application entry point
└── GSD-QUICK-START.md   # GSD setup guide
```

## Directory Purposes

**backend/:**
- Purpose: Python backend application
- Contains: FastAPI app, routers, scanner logic, services, models
- Key files: `main.py` (app setup), `models.py` (database models), `config.py` (settings)

**backend/routers/:**
- Purpose: API endpoint handlers organized by domain
- Contains: Router modules for dashboard, assets, strategies, setups, scans, journal, backtester, webhooks, chart_data
- Key files: Each router handles a specific API namespace (e.g., `/api/dashboard/*`)

**backend/scanner/:**
- Purpose: Core trading scanner engine and analysis logic
- Contains: Engine orchestration, condition evaluation, indicator calculations, data fetching, regime detection, level calculation, backtesting
- Key files: `engine.py` (main scan logic), `conditions.py` (condition evaluation), `indicators.py` (technical indicators)

**backend/services/:**
- Purpose: Background services and cross-cutting concerns
- Contains: Scheduler, log streaming, Telegram notifications
- Key files: `scheduler.py` (periodic scans), `log_streamer.py` (WebSocket log streaming)

**frontend/:**
- Purpose: Static web application
- Contains: HTML, CSS, JavaScript files
- Key files: `index.html` (main page), `js/app.js` (application logic), `js/api.js` (API client)

**frontend/js/:**
- Purpose: JavaScript application code
- Contains: Main app logic, API client, utilities, components
- Key files: `app.js` (view management, data rendering), `api.js` (HTTP requests), `utils.js` (formatting helpers)

## Key File Locations

**Entry Points:**
- `run.py`: Command-line entry point, starts Uvicorn server
- `backend/main.py`: FastAPI application definition and router registration
- `frontend/index.html`: Frontend entry point

**Configuration:**
- `backend/config.py`: Application settings (Pydantic Settings)
- `env.example`: Environment variables template
- `requirements.txt`: Python dependencies

**Core Logic:**
- `backend/scanner/engine.py`: Main scanner orchestration
- `backend/scanner/conditions.py`: Strategy condition evaluation
- `backend/scanner/indicators.py`: Technical indicator calculations
- `backend/scanner/data_fetcher.py`: Exchange API integration

**Database:**
- `backend/models.py`: SQLAlchemy ORM models
- `backend/database.py`: Database engine and session management
- `backend/schemas.py`: Pydantic validation schemas

**Testing:**
- Not detected - No test files found

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `data_fetcher.py`, `log_streamer.py`)
- JavaScript: `camelCase.js` (e.g., `app.js`, `api.js`)
- HTML/CSS: `kebab-case` (e.g., `index.html`, `styles.css`)

**Directories:**
- `snake_case` for Python modules (e.g., `backend/routers/`)
- `camelCase` for JavaScript modules (e.g., `frontend/js/components/`)

**Python:**
- Classes: `PascalCase` (e.g., `Asset`, `Strategy`, `Setup`)
- Functions/variables: `snake_case` (e.g., `run_scan`, `fetch_ohlcv`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `SETUP_EXPIRY_HOURS`)

**JavaScript:**
- Functions/variables: `camelCase` (e.g., `loadSetups`, `currentView`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `LOG_MAX`)

## Where to Add New Code

**New Feature:**
- Primary code: `backend/routers/[feature].py` for API endpoints
- Business logic: `backend/scanner/[feature].py` if scanner-related, or `backend/services/[feature].py` for services
- Frontend: `frontend/js/app.js` for view logic, `frontend/js/api.js` for API calls

**New Component/Module:**
- API router: `backend/routers/[name].py`, register in `backend/main.py`
- Scanner module: `backend/scanner/[name].py`, import in `engine.py` or relevant module
- Service: `backend/services/[name].py`, import where needed
- Frontend component: `frontend/js/components/[name].js`, import in `app.js`

**Utilities:**
- Shared helpers: `backend/scanner/[utility].py` or `frontend/js/utils.js`
- Database utilities: Add to `backend/database.py` or create `backend/utils.py`

**Database Changes:**
- Models: Add to `backend/models.py`
- Schemas: Add to `backend/schemas.py`
- Migrations: Use Alembic (not currently configured, but available)

## Special Directories

**.claude/:**
- Purpose: Claude Code configuration, commands, agents
- Generated: Yes (by GSD installer)
- Committed: Yes (should be committed)

**.planning/:**
- Purpose: GSD planning documents, codebase maps, project state
- Generated: Yes (by GSD commands)
- Committed: Yes (by default, configurable)

**__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No (should be in .gitignore)

---
*Structure analysis: 2026-02-17*
