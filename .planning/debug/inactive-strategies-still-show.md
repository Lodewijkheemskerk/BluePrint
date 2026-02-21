# Debug: Inactive Strategies Still Appear in List

**Issue:** When toggling a strategy to inactive, it still appears in the strategies list.

**Symptoms:**
- User toggles strategy active/inactive switch
- Strategy status updates (API call succeeds)
- Strategy list refreshes
- Inactive strategies still visible in the list

**Expected Behavior:**
- Only active strategies should be displayed, OR
- Inactive strategies should be visually distinct/filtered

**Investigation:**

1. **Backend Analysis:**
   - `backend/routers/strategies.py` line 19-21: `list_strategies()` endpoint returns ALL strategies
   - No filtering by `is_active` status
   - Returns all strategies regardless of active state

2. **Frontend Analysis:**
   - `frontend/js/app.js` line 285: Calls `api.getStrategies()` which gets all strategies
   - `frontend/js/app.js` line 293-320: Renders all strategies returned from API
   - No filtering logic in frontend

3. **Root Cause:**
   **The API endpoint `/api/strategies/` returns ALL strategies without filtering by `is_active` status. The frontend also doesn't filter the results - it displays all strategies returned from the API.**

   The toggle functionality works (updates `is_active` in database), but the list endpoint doesn't respect the filter, and the frontend doesn't filter either.

**Files Involved:**
- `backend/routers/strategies.py` (line 19-63 - list_strategies endpoint)
- `frontend/js/app.js` (line 283-324 - loadStrategies function)

**Suggested Fix:**
1. Add query parameter to filter by `is_active` in backend endpoint
2. OR filter strategies in frontend after receiving from API
3. OR add visual distinction for inactive strategies (grayed out, separate section, etc.)
