#!/usr/bin/env python3
"""UI Smoke Test: Dashboard im Browser laden, Screenshot erzeugen."""

from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8888"
OUT = Path("qa/ui")
OUT.mkdir(parents=True, exist_ok=True)

console_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    response = page.goto(URL, wait_until="networkidle", timeout=15000)
    page.screenshot(path=str(OUT / "ui-smoke.png"), full_page=True)
    title = page.title()
    body_text = page.locator("body").inner_text(timeout=5000)
    browser.close()

print("URL:", URL)
print("HTTP:", response.status if response else "no response")
print("Title:", title)
print("Body length:", len(body_text))
print("Body preview:", body_text[:200])
print("Console errors:", console_errors)

if response is None or response.status >= 400:
    raise SystemExit(f"FAIL: HTTP {response.status if response else 'no response'}")
if len(body_text.strip()) < 20:
    raise SystemExit("FAIL: UI body appears empty")
if console_errors:
    print(f"WARNING: {len(console_errors)} console errors detected")
    for e in console_errors[:5]:
        print(f"  - {e}")
else:
    print("SUCCESS: No console errors")
