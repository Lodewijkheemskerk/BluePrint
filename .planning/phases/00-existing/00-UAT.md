---
status: fixed
phase: 00-existing
source: [existing application codebase]
started: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Application loads and displays dashboard
expected: Navigate to the application URL. The dashboard (Setups view) should load and display: Top navigation bar with all view links (Setups, Strategies, Universe, Regime, Scans, Journal, Backtester, Logs), Statistics row showing: Active Setups, Strategies, Universe Size, Setups Today, Last Scan, Market regime indicator in top-right navigation, Active Setups table (or empty state message if no setups), Filter pills for All/Long/Short setups
result: pass

### 2. Navigation between views
expected: Click each navigation link (Setups, Strategies, Universe, Regime, Scans, Journal, Backtester, Logs). Each view should load and display its content. The active view should be highlighted in the navigation. URL should update appropriately.
result: pass

### 3. View active setups table
expected: On the Setups view, if setups exist, the table should display: Asset symbol, Strategy name, Direction badge, Status badge, Entry price, Stop loss, TP1/TP2/TP3, Risk:Reward ratio, Funding rate, Detection time. Each row should be clickable. If no setups exist, show empty state message.
result: pass

### 4. View setup details modal
expected: Click on a setup row in the table. A modal should open showing: Setup symbol and badges, Strategy name, Detection date, Entry/Stop/TP levels, Risk:Reward ratio, Funding rate, Market regime, Performance indicators (TP1/TP2/TP3/SL hit status), TradingView link button, Log Trade button, Price chart with setup levels drawn (Entry, SL, TP1, TP2 lines)
result: issue
reported: "When i click on a setup. Nothing opens"
severity: major

### 5. View strategies list
expected: Navigate to Strategies view. Should display list of strategy cards showing: Strategy name, Direction badge, Active/inactive toggle, Delete button, Description (if provided), Metadata (Setups count, Win rate, Valid regimes), Condition tags showing condition types and timeframes. If no strategies exist, show empty state message.
result: pass

### 6. Create new strategy
expected: Click "New Strategy" button. Modal opens with form fields: Name (required), Direction dropdown (Long/Short/Both), Description, Conditions section with ability to add multiple conditions. Each condition row has: Condition type dropdown, Timeframe dropdown, Parameters JSON input, Required toggle. Click "Create Strategy" - strategy is created, modal closes, toast notification shows success, strategies list refreshes with new strategy.
result: pass

### 7. Toggle strategy active/inactive
expected: On a strategy card, toggle the active/inactive switch. Strategy status should update immediately. API call should succeed. Strategy list should reflect the change.
result: issue
reported: "when i toggle strategy of it still shows them in the list."
severity: major

### 8. Delete strategy
expected: Click delete button on a strategy card. Confirmation dialog appears. Confirm deletion - strategy is removed, toast notification shows success, strategies list refreshes without the deleted strategy.
result: pass

### 9. View asset universe
expected: Navigate to Universe view. Table displays: Symbol, Base currency, Source (dynamic/watchlist), Market cap rank, Status (Active/Inactive), Actions (TradingView link, Remove/Activate button). If no assets exist, show appropriate empty state.
result: pass

### 10. Add asset to watchlist
expected: In Universe view, enter a symbol like "BTC/USDT" in the input field. Click "Add to Watchlist" button. Asset is added, input field clears, toast notification shows success, universe table refreshes with new asset.
result: pass

### 11. Remove/activate asset
expected: In Universe view, click "Remove" button on an active asset - asset becomes inactive. Click "Activate" button on an inactive asset - asset becomes active. Table updates immediately to reflect status change.
result: pass

### 12. View market regime
expected: Navigate to Regime view. Should display: Current Market Regime badge with description, BTC Trend value, Confidence percentage. If no regime data exists, show empty state message prompting to run a scan.
result: pass

### 13. View scan history
expected: Navigate to Scans view. Table displays: Scan ID, Started timestamp, Finished timestamp (or spinner if running), Assets scanned count, Setups found count, Market regime badge, Status badge. "Trigger Scan" button is visible. If no scans exist, show empty state message.
result: pass

### 14. Trigger scan
expected: Click "Trigger Scan" button. Button changes to "Cancel Scan" with spinner. Toast notification shows "Scan triggered — running in background". Scan status polling begins. Scan appears in table with "running" status and spinner. When scan completes, button returns to "Trigger Scan", toast shows "Scan finished", table updates with completed scan data.
result: issue
reported: "I dont see scan running in table. It does show up when completed. rest is also pass"
severity: minor

### 15. Cancel running scan
expected: While scan is running, click "Cancel Scan" button. Button changes to "Cancelling…" with spinner. Cancellation request is sent. When scan actually stops, button returns to "Trigger Scan" state, polling stops.
result: pass

### 16. View journal entries
expected: Navigate to Journal view. Statistics row shows: Total Trades (30d), Win Rate, Avg R, Total P&L. Table displays: Date, Asset symbol, Strategy name, Direction badge, Action badge, Outcome, Planned R:R, P&L (R), Tags. If no entries exist, show empty state message.
result: pass

### 17. Create journal entry manually
expected: Click "Log Trade" button. Modal opens with form fields: Symbol, Strategy, Direction, Action, Outcome, Entry/Stop/TP prices, P&L (R-multiple), Planned R:R, Tags, Notes. Fill in required fields and click "Save Entry". Entry is created, modal closes, toast shows success, journal table refreshes with new entry.
result: pass

### 18. Create journal entry from setup
expected: Open a setup detail modal, click "Log Trade" button. Journal modal opens with fields pre-filled from setup: Symbol, Strategy, Direction, Entry/Stop/TP prices, Planned R:R, Tags (from setup metadata), Notes (with setup details). User can edit and save. Entry is linked to setup via setup_id.
result: pass

### 19. Run backtest
expected: Navigate to Backtester view. Select a strategy from dropdown, choose timeframe (Daily/4H/1H), optionally enter symbols (comma-separated) or leave blank for universe. Click "Run Backtest" button. Results display: Total Setups, Win Rate, Avg R:R, Max Drawdown, Setups/Month, Symbols Tested. If setup details exist, show table with: Symbol, Entry Date, Entry, SL, TP1, Result, P&L (R). Results are color-coded (green for wins, red for losses).
result: issue
reported: "when symbols is entered in the textbox. the background turns white. this is ugly. rest pass"
severity: cosmetic

### 20. View live logs
expected: Navigate to Logs view. WebSocket connection establishes (status shows "Connected"). Log entries stream in real-time displaying: Timestamp, Log level (DEBUG/INFO/WARNING/ERROR), Logger name, Message. Log level pills filter logs (All/Debug/Info/Warn/Error). Search input filters logs by text. Line count updates showing visible lines. Pause button pauses/resumes log streaming. Clear button clears displayed logs. Export button downloads logs as text file.
result: pass

### 21. Filter and search logs
expected: In Logs view, click a log level pill (e.g., "Error") - only logs of that level are displayed. Type in search box - logs are filtered by matching text in message or logger name. Search text is highlighted in log messages. Line count updates to show filtered count.
result: pass

### 22. Setup chart displays correctly
expected: Open setup detail modal. Chart container loads TradingView Lightweight Charts. Candlestick chart displays with OHLCV data. Volume histogram displays below price chart. Setup levels are drawn as horizontal lines: Entry (blue dashed), Stop Loss (red dashed), TP1 (green dashed), TP2 (green solid). Chart auto-fits to content. Chart resizes when modal is resized.
result: pass

### 23. Dashboard statistics update
expected: On Setups view, statistics row displays accurate counts: Active Setups matches count in table, Active Strategies matches count of active strategies, Universe Size matches active assets count, Setups Today shows count from today, Last Scan shows time ago or "Never". Market regime badge displays in top-right navigation.
result: pass

### 24. Empty states display correctly
expected: When no data exists for a view, appropriate empty state messages are shown: "No active setups" with helpful text, "No strategies yet" with prompt to create, "No scan history" with prompt to trigger scan, "No journal entries" with prompt to log trade, "No regime data" with prompt to run scan, "No assets" with prompt to add.
result: pass

### 25. Error handling and toast notifications
expected: When API calls fail, error toast notifications appear with error message. When operations succeed, success toast notifications appear. Toasts auto-dismiss after a few seconds. Multiple toasts stack vertically. Network errors are handled gracefully without breaking the UI.
result: pass

## Summary

total: 25
passed: 22
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "Click on a setup row in the table. A modal should open showing setup details"
  status: failed
  reason: "User reported: When i click on a setup. Nothing opens"
  severity: major
  test: 4
  root_cause: "onclick handler may not be accessible when table renders, or JavaScript error preventing execution. window.app.showSetupDetail() exists but may not be available at render time."
  artifacts:
    - path: "frontend/js/app.js"
      issue: "onclick handler set on table rows, but window.app may not be available at render time"
    - path: "frontend/index.html"
      issue: "Modal definition exists but not being triggered"
  missing:
    - "Ensure window.app is defined before table rendering"
    - "Add error handling in showSetupDetail() to catch errors"
    - "Consider using event delegation instead of inline onclick"
  debug_session: ".planning/debug/setup-modal-not-opening.md"

- truth: "On a strategy card, toggle the active/inactive switch. Strategy status should update immediately. Strategy list should reflect the change."
  status: failed
  reason: "User reported: when i toggle strategy of it still shows them in the list."
  severity: major
  test: 7
  root_cause: "API endpoint /api/strategies/ returns ALL strategies without filtering by is_active. Frontend also doesn't filter - displays all strategies returned from API."
  artifacts:
    - path: "backend/routers/strategies.py"
      issue: "list_strategies() endpoint returns all strategies, no filtering by is_active"
    - path: "frontend/js/app.js"
      issue: "loadStrategies() displays all strategies without filtering"
  missing:
    - "Add query parameter to filter by is_active in backend endpoint"
    - "OR filter strategies in frontend after receiving from API"
    - "OR add visual distinction for inactive strategies"
  debug_session: ".planning/debug/inactive-strategies-still-show.md"

- truth: "Click 'Trigger Scan' button. Scan appears in table with 'running' status and spinner."
  status: failed
  reason: "User reported: I dont see scan running in table. It does show up when completed. rest is also pass"
  severity: minor
  test: 14
  root_cause: "trigger_scan() starts background thread but doesn't return scan_id. Scan log is created inside run_scan() which runs asynchronously. When loadScans() is called immediately after triggering, the scan log doesn't exist in database yet, so it won't appear in logs array."
  artifacts:
    - path: "backend/routers/scans.py"
      issue: "trigger_scan() doesn't return scan_id, scan log created in background thread"
    - path: "backend/scanner/engine.py"
      issue: "Scan log created inside run_scan() after thread starts"
    - path: "frontend/js/app.js"
      issue: "loadScans() checks for activeScanId but log doesn't exist in array yet"
  missing:
    - "Create scan log BEFORE starting background thread in trigger_scan()"
    - "Return scan_id immediately from trigger_scan()"
    - "Frontend can add placeholder row or poll for scan log"
  debug_session: ".planning/debug/scan-running-not-visible.md"

- truth: "Backtester view input fields have consistent styling"
  status: failed
  reason: "User reported: when symbols is entered in the textbox. the background turns white. this is ugly. rest pass"
  severity: cosmetic
  test: 19
  root_cause: "CSS doesn't explicitly set background-color in :focus state, and browser autofill styling is overriding the dark background with white. Browser autofill styles can override custom CSS."
  artifacts:
    - path: "frontend/css/styles.css"
      issue: ".form-input:focus doesn't explicitly set background-color, autofill styles override"
    - path: "frontend/index.html"
      issue: "bt-symbols input field affected by browser autofill styling"
  missing:
    - "Add explicit background-color: var(--bg-primary) !important; to .form-input:focus"
    - "Add autofill pseudo-class styling: .form-input:-webkit-autofill"
    - "Ensure consistent dark background in all input states"
  debug_session: ".planning/debug/backtester-input-white-background.md"
