# Debug: Setup Detail Modal Not Opening

**Issue:** Clicking on a setup row in the table does not open the modal.

**Symptoms:**
- User clicks on setup row
- Nothing happens - modal does not appear
- No visible errors in console (user didn't report errors)

**Expected Behavior:**
- Clicking a setup row should call `window.app.showSetupDetail(setupId)`
- Modal should open showing setup details with chart

**Investigation:**

1. **Code Analysis:**
   - `frontend/js/app.js` line 93: Table rows have `onclick="window.app.showSetupDetail(${s.id})"`
   - `frontend/js/app.js` line 119: `showSetupDetail()` function is defined
   - `frontend/js/app.js` line 1165: Function is exposed on `window.app.showSetupDetail`

2. **Potential Issues:**
   - `window.app` is defined at module level (line 1163) but might not be available when onclick fires
   - The onclick handler uses template literal `${s.id}` which should work
   - Function exists and is properly exposed

3. **Root Cause:**
   The onclick handler is set correctly, but there might be a timing issue or the function might not be accessible. However, more likely the issue is that the table is rendered before `window.app` is fully initialized, OR there's a JavaScript error that's silently failing.

   **Most Likely Cause:** The onclick attribute is set correctly, but `window.app` might not be available at the time the table is rendered, OR there's an error in `showSetupDetail()` that's preventing execution.

**Files Involved:**
- `frontend/js/app.js` (lines 93, 119-165, 1163-1186)
- `frontend/index.html` (line 210 - modal definition)

**Suggested Fix:**
1. Check browser console for JavaScript errors
2. Ensure `window.app` is defined before table is rendered
3. Consider using event delegation instead of inline onclick handlers
4. Add error handling in `showSetupDetail()` to catch and log errors
