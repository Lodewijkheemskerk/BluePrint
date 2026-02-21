# Coding Conventions

**Analysis Date:** 2026-02-17

## Naming Patterns

**Files:**
- Python: `snake_case.py` (e.g., `data_fetcher.py`, `log_streamer.py`)
- JavaScript: `camelCase.js` (e.g., `app.js`, `api.js`)
- HTML/CSS: `kebab-case` (e.g., `index.html`, `styles.css`)

**Functions:**
- Python: `snake_case` (e.g., `run_scan`, `fetch_ohlcv`, `add_moving_average`)
- JavaScript: `camelCase` (e.g., `loadSetups`, `showSetupDetail`, `formatPrice`)

**Variables:**
- Python: `snake_case` (e.g., `scan_log`, `current_regime`, `assets_scanned`)
- JavaScript: `camelCase` (e.g., `currentView`, `logEntries`, `chartInstance`)

**Types:**
- Python: `PascalCase` for classes (e.g., `Asset`, `Strategy`, `Setup`, `ScanLog`)
- JavaScript: No explicit type system (vanilla JS)

**Constants:**
- Both: `UPPER_SNAKE_CASE` (e.g., `SETUP_EXPIRY_HOURS`, `LOG_MAX`)

## Code Style

**Formatting:**
- Python: No formatter detected (no `.black`, `.autopep8`, etc.)
- JavaScript: No formatter detected (no `.prettierrc`, etc.)
- Indentation: 4 spaces for Python, appears consistent

**Linting:**
- Python: No linter config detected (no `.pylintrc`, `pyproject.toml` with linting)
- JavaScript: No linter config detected (no `.eslintrc`, etc.)

## Import Organization

**Order:**
1. Standard library imports (e.g., `import logging`, `from datetime import datetime`)
2. Third-party imports (e.g., `from fastapi import APIRouter`, `import pandas as pd`)
3. Local imports (e.g., `from backend.models import Asset`, `from backend.database import get_db`)

**Path Aliases:**
- Python: Relative imports from `backend` package (e.g., `from backend.scanner.engine import run_scan`)
- JavaScript: No path aliases, relative paths or global scope

## Error Handling

**Patterns:**
- Try-except blocks with logging: `try: ... except Exception as e: logger.error(...)`
- Graceful degradation: Functions return `None` on failure, calling code checks for `None`
- Error collection: Scanner errors collected in list, stored as JSON in `ScanLog.errors`
- API errors: FastAPI exception handling, returns HTTP status codes

**Example from `backend/scanner/data_fetcher.py`:**
```python
try:
    # ... fetch logic ...
    return df
except Exception as e:
    logger.error(f"Error fetching {symbol} ({timeframe}): {e}")
    return None
```

## Logging

**Framework:** Python `logging` module

**Patterns:**
- Logger per module: `logger = logging.getLogger(__name__)`
- Log levels: INFO for normal operations, WARNING for recoverable issues, ERROR for failures
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- WebSocket streaming: All logs streamed to frontend via `backend/services/log_streamer.py`

**When to Log:**
- INFO: Scan start/complete, setup detection, scheduler events
- WARNING: Missing data, skipped operations, optional feature failures
- ERROR: Exceptions, API failures, critical errors

## Comments

**When to Comment:**
- Module docstrings: All Python modules have `"""` docstrings at top
- Function docstrings: Complex functions have docstrings explaining parameters and return values
- Inline comments: Used sparingly for non-obvious logic (e.g., `# Normalize expires_at to timezone-aware if it's naive (SQLite issue)`)

**JSDoc/TSDoc:**
- Not used - Vanilla JavaScript, no type annotations

## Function Design

**Size:**
- Functions are generally focused and single-purpose
- Some longer functions (e.g., `run_scan` ~200 lines) handle orchestration but are well-structured

**Parameters:**
- Python: Type hints used where present (e.g., `def fetch_ohlcv(symbol: str, timeframe: str = "1d", limit: int = 200)`)
- Default values used for optional parameters
- Database sessions passed via FastAPI dependency injection

**Return Values:**
- Python: Type hints indicate return types (e.g., `-> Optional[pd.DataFrame]`, `-> ScanLog`)
- Functions return `None` on failure, actual data on success
- Consistent return patterns across similar functions

## Module Design

**Exports:**
- Python: Functions and classes exported at module level, imported explicitly
- JavaScript: Functions attached to `window.app` object for global access, ES6 modules not used

**Barrel Files:**
- Not used - Direct imports from specific modules

**Module Organization:**
- Python: One class/function per logical unit, modules organized by domain (routers, scanner, services)
- JavaScript: Single large `app.js` file with all view logic, `api.js` for HTTP calls, `utils.js` for helpers

## Code Patterns

**Database Sessions:**
- FastAPI dependency injection: `db: Session = Depends(get_db)`
- Context managers: `try: ... finally: db.close()` for manual session management

**Async/Await:**
- FastAPI routes are async where appropriate
- Background tasks use threading (scheduler) or async (WebSocket)

**Data Processing:**
- Pandas DataFrames for OHLCV data manipulation
- Functions return DataFrames with added columns (indicators)
- Idempotent indicator functions (check if column exists before adding)

---
*Convention analysis: 2026-02-17*
