# Live-QA auf Self-Hosted-Runner

## Ziel

Playwright-Visual-Tests und Accessibility-Tests benötigen echte GPU-Dienste (llama-server, SearXNG, Ollama) — das ist in GitHub Actions nicht möglich. Daher: **Live-QA nur auf Self-Hosted-Runnern**.

## Voraussetzungen (Runner)

| Dienst | Version | Port | Zweck |
|---|---|---|---|
| llama-server (Gemma 4) | neueste | 8081 | Chat/Summary |
| Ollama | ≥0.5 | 11434 | Embedding |
| SearXNG | ≥2026.5 | 8080 | Websuche |
| Tor (optional) | ≥0.4 | 9050 | Darknet |
| Chromium | neueste | — | Playwright |

## Workflow

```yaml
# .github/workflows/live-qa.yml
name: Live-QA Evidence

on:
  workflow_dispatch:
  schedule:
    - cron: '0 6 * * 1'  # Montag 6:00 UTC

jobs:
  live-qa:
    runs-on: [self-hosted, gpu, researcher]
    timeout-minutes: 30

    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install playwright
          playwright install chromium

      - name: Health check — alle Dienste
        run: |
          PYTHONPATH=. python3 scripts/runtime_smoke.py

      - name: Research Happy Path (CLI)
        run: |
          PYTHONPATH=. python3 scripts/research_happy_path.py --strict

      - name: Playwright Visual Tests
        run: |
          RUN_PLAYWRIGHT_TESTS=true python3 -m pytest \
            tests/playwright/test_dashboard_viewports.py -v

      - name: Playwright Accessibility Tests
        run: |
          RUN_PLAYWRIGHT_TESTS=true python3 -m pytest \
            tests/playwright/test_dashboard_accessibility.py -v

      - name: Upload QA Artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: live-qa-evidence
          path: |
            qa/live/artifacts/
            reports/research/
            reports/evaluation/

      - name: Generate Report
        if: always()
        run: |
          echo "## Live-QA Report" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Datum:** $(date)" >> $GITHUB_STEP_SUMMARY
          echo "- **Status:** ${{ job.status }}" >> $GITHUB_STEP_SUMMARY
```

## Runner-Einrichtung (einmalig)

```bash
# Auf dem Self-Hosted-Runner:
sudo apt install docker.io docker-compose
pip install playwright
playwright install chromium

# LM Studio / Ollama / SearXNG als systemd-Services
sudo systemctl enable --now ollama
sudo systemctl enable --now docker

# SearXNG:
docker run -d --name searxng \
  -p 127.0.0.1:8080:8080 \
  -v $(pwd)/searxng/settings.yml:/etc/searxng/settings.yml:ro \
  searxng/searxng:latest

# Gemma 4 (via serve script):
./serve_gemma4_obliterated_researcher.sh &
```

## Bekannte Einschränkungen

1. **SSE blockiert Playwright**: `networkidle`-Wait hängt bei SSE-Stream → `domcontentloaded` verwenden
2. **Gemma 4 braucht GPU**: Kein Fallback auf CPU bei Self-Hosted
3. **SearXNG CAPTCHA**: DuckDuckGo-Engine kann CAPTCHA werfen → Fallback-Engine konfigurieren
4. **VRAM**: ≥6 GB frei für Gemma 4 + Embedding gleichzeitig

## Referenzen

- `qa/live/live-test-plan.md` — Test-Flows
- `tests/playwright/` — Playwright-Tests
- `scripts/runtime_smoke.py` — Healthcheck
- `docs/development/local-runbook.md` — Service-Start
