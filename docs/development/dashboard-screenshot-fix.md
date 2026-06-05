# Dashboard Screenshot Fix — SSE-Blocking Resolution

**Date:** 2026-06-04  
**Phase:** 8 — Quality Hardening  
**Issue:** #143

## Problem

Playwright screenshots of the Dashboard (`http://127.0.0.1:8888/`) fail with a timeout:

```
Error: waiting for fonts to load
Timeout 30000ms exceeded
```

### Root Cause

The Dashboard's default `index.html` opens a **persistent SSE (Server-Sent Events)**
connection to `/api/gpu/stream` on page load (line 197: `new EventSource('/api/gpu/stream')`).

This connection:
1. Stays open indefinitely (server pushes GPU data every 2 seconds)
2. Causes Playwright's `networkidle` wait to never resolve
3. Causes Playwright's font-loading wait to timeout (fonts finished loading,
   but the page remains in a "loading" state as the SSE connection is active)

### Why this is not a bug in the Dashboard

The SSE stream is the intended behavior for the live dashboard — it provides
real-time GPU metrics. The issue is specific to Playwright's screenshot
mechanism, which expects pages to be "fully loaded" with no ongoing
network activity.

## Solution: Static Fallback Page

Created `/dashboard/static/static-fallback.html` — a version of the dashboard
that uses a **one-shot `/api/gpu` JSON fetch** instead of the persistent SSE
stream.

### Key Differences from index.html

| Feature | index.html (Live) | static-fallback.html (Screenshot) |
|---------|-------------------|-----------------------------------|
| Data source | SSE stream (`/api/gpu/stream`) | One-shot JSON (`/api/gpu`) |
| Connection | Persistent, never closes | Single fetch, completes immediately |
| Auto-reconnect | Yes (exponential backoff) | No |
| Real-time updates | Every 2 seconds | One snapshot |
| Playwright compatible | ❌ Hangs on font-loading | ✅ Completes immediately |
| URL | `/` or `/index.html` | `/static-fallback.html` |

### Usage in Playwright Tests

```python
# BEFORE (hangs on SSE):
await page.goto("http://127.0.0.1:8888/")

# AFTER (static snapshot):
await page.goto("http://127.0.0.1:8888/static-fallback.html")
await page.wait_for_load_state("networkidle")  # Works!
await page.screenshot(path="dashboard.png")
```

### Alternative Solutions (Not Chosen)

| Option | Description | Reason Rejected |
|--------|-------------|----------------|
| `--disable-font-loading` | Chromium flag | Doesn't fix the SSE open-connection issue |
| Font-ready-timeout | Browser argument | SSE connection still keeps page "loading" |
| Screenshot only `/api/gpu` | JSON endpoint only | No visual dashboard UI for regression testing |
| Modify SSE to close after first event | Change server behavior | Breaks live dashboard functionality |

The static fallback page was chosen because:
- It preserves the visual layout for screenshot comparison
- It requires no server-side changes
- It's explicitly documented as being for automated testing
- The live SSE dashboard remains unchanged for real users

## Dashboard Route Update

The server (`dashboard/server.py`) already serves any file from `dashboard/static/`,
so no code changes are needed. The fallback is accessible at:

```
http://127.0.0.1:8888/static-fallback.html
```

## Screenshot Test Update

```python
# In tests/playwright/test_dashboard_*.py:
DASHBOARD_URL = "http://127.0.0.1:8888"
FALLBACK_URL = f"{DASHBOARD_URL}/static-fallback.html"

# Use FALLBACK_URL for visual regression tests
# Keep DASHBOARD_URL for SSE-specific tests (e.g., test_gpu_sse_stream)
```

## Verification

```bash
# Start dashboard
python3 -m dashboard.server &

# Static page loads immediately
curl -s http://127.0.0.1:8888/static-fallback.html | head -5
# → <!DOCTYPE html>...

# JSON endpoint works
curl -s http://127.0.0.1:8888/api/gpu | python3 -m json.tool | head -5

# Playwright screenshot now works
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://127.0.0.1:8888/static-fallback.html')
    page.wait_for_load_state('networkidle')
    page.screenshot(path='/tmp/dashboard-fallback.png')
    browser.close()
    print('✅ Screenshot captured')
"
```
