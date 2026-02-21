# Codebase Concerns

**Analysis Date:** 2026-02-17

## Tech Debt

**No Test Coverage:**
- Issue: No testing infrastructure or test files present
- Files: Entire codebase
- Impact: Changes may introduce regressions, no confidence in refactoring, manual testing required
- Fix approach: Add pytest for backend, consider test framework for frontend. Start with critical paths (scanner engine, condition evaluation, API endpoints)

**No Code Formatting/Linting:**
- Issue: No formatter (Black, autopep8) or linter (pylint, flake8) configured
- Files: All Python files
- Impact: Inconsistent code style, potential bugs from style issues, harder code reviews
- Fix approach: Add Black for formatting, pylint or ruff for linting. Add pre-commit hooks or CI checks

**Large JavaScript File:**
- Issue: `frontend/js/app.js` is ~1200 lines, contains all view logic
- Files: `frontend/js/app.js`
- Impact: Hard to maintain, difficult to navigate, potential for merge conflicts
- Fix approach: Split into view-specific modules (setups.js, strategies.js, journal.js, etc.) or use a module system

**No Database Migrations:**
- Issue: Alembic is in requirements but no migrations directory or migration setup
- Files: `backend/models.py`, `backend/database.py`
- Impact: Schema changes require manual SQL or database recreation, no version control for schema
- Fix approach: Initialize Alembic, create initial migration, document migration workflow

**SQLite Timezone Handling:**
- Issue: Manual timezone normalization in code (see `_update_setup_lifecycle` in `engine.py`)
- Files: `backend/scanner/engine.py` (line ~400)
- Impact: Potential timezone bugs, workaround code indicates underlying issue
- Fix approach: Use timezone-aware datetimes consistently, or migrate to PostgreSQL with proper timezone support

## Known Bugs

**None explicitly marked:**
- No TODO/FIXME/HACK comments found in codebase
- No bug tracking system detected

## Security Considerations

**No Authentication:**
- Risk: API endpoints are publicly accessible, no access control
- Files: All `backend/routers/*.py` endpoints
- Current mitigation: Likely intended for local/development use only
- Recommendations: Add authentication if deploying to production, or document that this is a local-only tool

**Environment Variables:**
- Risk: Secrets in `.env` file (if present) could be accidentally committed
- Files: `.env` (not in repo, but `env.example` is)
- Current mitigation: `.env` should be in `.gitignore` (not verified)
- Recommendations: Verify `.gitignore` includes `.env`, document secret management

**SQL Injection:**
- Risk: Low - Using SQLAlchemy ORM which parameterizes queries
- Files: All database access via `backend/models.py`
- Current mitigation: ORM prevents most SQL injection
- Recommendations: Continue using ORM, avoid raw SQL queries

## Performance Bottlenecks

**Sequential Asset Scanning:**
- Problem: Scanner processes assets sequentially in loop (`engine.py` line ~132)
- Files: `backend/scanner/engine.py`
- Cause: Single-threaded processing of each asset
- Improvement path: Consider parallel processing for independent assets (ThreadPoolExecutor), but be mindful of exchange API rate limits

**No Caching:**
- Problem: Exchange API calls made on every scan, no caching of market data
- Files: `backend/scanner/data_fetcher.py`
- Cause: Fresh data required for accuracy, but some data (e.g., top coins list) could be cached
- Improvement path: Add caching layer for stable data (universe list), use TTL for time-sensitive data

**Large DataFrame Operations:**
- Problem: Multiple indicator calculations on DataFrames, potential memory usage
- Files: `backend/scanner/indicators.py`
- Cause: All indicators added to single DataFrame, may grow large with many timeframes
- Improvement path: Profile memory usage, consider lazy evaluation or selective indicator calculation

## Fragile Areas

**Exchange API Integration:**
- Files: `backend/scanner/data_fetcher.py`
- Why fragile: Depends on external API (Binance via ccxt), network issues, API changes, rate limits
- Safe modification: Add retry logic, better error handling, fallback mechanisms
- Test coverage: None - Critical path with no tests

**Database Schema Changes:**
- Files: `backend/models.py`, `backend/database.py`
- Why fragile: Manual schema upgrades (see `_ensure_journal_tp_columns`), no migration system
- Safe modification: Initialize Alembic, create proper migrations before schema changes
- Test coverage: None

**Frontend State Management:**
- Files: `frontend/js/app.js`
- Why fragile: Global variables, no state management framework, manual DOM manipulation
- Safe modification: Consider state management pattern or framework, refactor incrementally
- Test coverage: None

## Scaling Limits

**SQLite Database:**
- Current capacity: Suitable for development and small-scale use
- Limit: Concurrent writes, large datasets, production workloads
- Scaling path: Migrate to PostgreSQL via `DATABASE_URL` configuration

**Single-threaded Scanning:**
- Current capacity: Sequential processing of assets
- Limit: Scan time grows linearly with number of assets
- Scaling path: Parallel processing with rate limit awareness, or async processing

**In-memory Log Storage:**
- Current capacity: `LOG_MAX = 5000` entries in frontend
- Limit: Memory usage, browser performance with large logs
- Scaling path: Implement pagination or virtual scrolling for log viewer

## Dependencies at Risk

**pandas-ta 0.3.14b1:**
- Risk: Beta version, may have stability issues
- Impact: Indicator calculations could fail or produce incorrect results
- Migration plan: Monitor for stable release, consider alternative (TA-Lib) or custom implementations

**No dependency version pinning:**
- Risk: `requirements.txt` has versions but no lock file (Pipfile.lock, poetry.lock)
- Impact: Dependency updates could break application
- Migration plan: Consider using pip-tools, Poetry, or Pipenv for dependency locking

## Missing Critical Features

**No Error Recovery:**
- Problem: Scanner fails completely if exchange API is down
- Blocks: Cannot continue scanning other assets, no graceful degradation
- Recommendation: Add retry logic, continue with cached data if available, skip failed assets

**No Backtest Validation:**
- Problem: Backtester exists but no validation of results
- Blocks: Cannot verify strategy performance claims
- Recommendation: Add validation, compare against known results, document assumptions

## Test Coverage Gaps

**All Areas:**
- What's not tested: Entire codebase has zero test coverage
- Files: All Python and JavaScript files
- Risk: High - Any change could break functionality
- Priority: High - Critical for maintainability

**Critical Paths:**
- Scanner engine: No tests for scan orchestration, setup creation, lifecycle management
- Condition evaluation: No tests for condition logic, edge cases
- Indicator calculations: No tests for mathematical correctness
- API endpoints: No integration tests for request/response handling

---
*Concerns audit: 2026-02-17*
