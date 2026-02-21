# Debug: Scan Running Status Not Visible in Table

**Issue:** When a scan is triggered, it doesn't appear in the scan history table until it completes.

**Symptoms:**
- User clicks "Trigger Scan" button
- Button changes to "Cancel Scan" (working)
- Toast shows "Scan triggered" (working)
- Scan does NOT appear in table with "running" status
- Scan only appears in table after completion

**Expected Behavior:**
- Scan should appear in table immediately with "running" status and spinner
- Table should show the active scan while it's running

**Investigation:**

1. **Backend Analysis:**
   - `backend/routers/scans.py` line 44-61: `trigger_scan()` starts background thread but returns `scan_id=None`
   - `backend/scanner/engine.py` line 77-80: Scan log is created INSIDE `run_scan()` function
   - Scan log is created in background thread, not immediately

2. **Frontend Analysis:**
   - `frontend/js/app.js` line 444-506: `loadScans()` fetches logs and status
   - Line 451: Gets `activeScanId` from status
   - Line 473-489: Renders logs, checks if `activeScanId === l.id` to show spinner
   - Problem: If scan log doesn't exist in `logs` array yet, it won't show

3. **Root Cause:**
   **When a scan is triggered, `trigger_scan()` starts a background thread but doesn't return the scan_id. The scan log is created inside `run_scan()` which runs asynchronously. When `loadScans()` is called immediately after triggering, the scan log might not exist in the database yet, so it won't appear in the logs array. The frontend checks `activeScanId === l.id` but if the log doesn't exist in the array, it can't display it.**

**Files Involved:**
- `backend/routers/scans.py` (line 44-61 - trigger_scan endpoint)
- `backend/scanner/engine.py` (line 77-80 - scan log creation)
- `frontend/js/app.js` (line 444-506 - loadScans function)

**Suggested Fix:**
1. Create scan log BEFORE starting background thread in `trigger_scan()`
2. Return the scan_id immediately from `trigger_scan()`
3. Frontend can then add a placeholder row or poll for the scan log
4. OR: Frontend can create a temporary "running" entry when scan is triggered, then replace it when real log appears
