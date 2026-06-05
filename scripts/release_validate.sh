#!/bin/bash
# Release validation script for v0.2.4
set -e

echo "=== CLEANUP ==="
pkill -9 -f "dashboard.server" 2>/dev/null || true
sleep 1
fuser -k 8888/tcp 2>/dev/null || true
sleep 1

echo "=== START DASHBOARD ==="
cd /home/xxammaxx/Schreibtisch/Researcher
python3 -m dashboard.server &
DASH_PID=$!
sleep 3

echo "=== VERIFY DASHBOARD ==="
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8888/)
echo "HTTP Status: $HTTP"

if [ "$HTTP" != "200" ]; then
    echo "Dashboard not responding!"
    exit 1
fi

echo "=== HEALTH ==="
curl -s --max-time 5 http://127.0.0.1:8888/health
echo ""

echo "=== GPU API ==="
curl -s --max-time 5 http://127.0.0.1:8888/api/gpu | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'GPU: {d[\"gpu_name\"]}')
print(f'Util: {d[\"gpu_utilization\"]}%')
print(f'VRAM: {d[\"memory_used_mib\"]}/{d[\"memory_total_mib\"]} MiB')
print(f'Temp: {d[\"temperature_c\"]}C')
print(f'Warning: {d[\"warning_level\"]}')
"

echo "=== PLAYWRIGHT SCREENSHOT ==="
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('http://127.0.0.1:8888/', wait_until='domcontentloaded', timeout=15000)
    page.wait_for_selector('#gpu-name', timeout=10000)
    h1 = page.locator('h1').inner_text()
    gpu = page.locator('#gpu-name').inner_text()
    cards = page.locator('#metrics .card').count()
    print(f'Title: {h1}')
    print(f'GPU: {gpu}')
    print(f'Metric cards: {cards}')
    page.screenshot(path='reports/release_validation/screenshots/dashboard_1920x1080.png', full_page=True)
    print('Screenshot saved.')
    browser.close()
"

echo "=== DONE ==="
kill $DASH_PID 2>/dev/null || true
