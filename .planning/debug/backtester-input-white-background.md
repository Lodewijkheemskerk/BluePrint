# Debug: Backtester Input Field White Background

**Issue:** When text is entered in the backtester symbols input field, the background turns white (ugly).

**Symptoms:**
- User enters text in "Symbols" input field in Backtester view
- Input field background changes to white
- This looks ugly/out of place with dark theme

**Expected Behavior:**
- Input field should maintain dark background color when text is entered
- Should be consistent with other form inputs

**Investigation:**

1. **CSS Analysis:**
   - `frontend/css/styles.css` line 315-327: `.form-input` has `background: var(--bg-primary)` (dark)
   - Line 329-334: `.form-input:focus` only changes `border-color`, not background
   - No explicit background-color in focus state

2. **Browser Behavior:**
   - Some browsers (especially Chrome) apply white background on autofill
   - Browser autofill styling can override custom CSS
   - When user types, browser might apply autofill styles

3. **Root Cause:**
   **The CSS doesn't explicitly set `background-color` in the `:focus` state, and browser autofill styling is likely overriding the dark background with white. The `background` property is set in the base `.form-input` rule, but browsers can override this with autofill styles.**

**Files Involved:**
- `frontend/css/styles.css` (line 315-334 - form-input styles)
- `frontend/index.html` (line 162 - bt-symbols input)

**Suggested Fix:**
1. Add explicit `background-color: var(--bg-primary) !important;` to `.form-input:focus`
2. Add autofill pseudo-class styling: `.form-input:-webkit-autofill { background-color: var(--bg-primary) !important; }`
3. Ensure consistent dark background in all input states
