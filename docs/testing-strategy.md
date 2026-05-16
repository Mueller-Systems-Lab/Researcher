# Teststrategie — Researcher (T-018)

## Übersicht

Diese Datei dokumentiert die Teststrategie für das Researcher-System.
Ziel: 100 % Codeabdeckung der Kernmodule mit Unit-, Integrations-,
E2E- und visuellen Tests (Playwright).

## Testpyramide

```
         ⬆ E2E (Playwright + laufende Dienste)
        ⬆⬆ Integration (mehrere Module)
       ⬆⬆⬆ Unit (ein Modul isoliert)
      ⬆⬆⬆⬆ Statische Analyse (mypy, ruff, bandit)
```

## Testebenen

### 1. Statische Analyse

| Tool | Befehl | Ziel |
|------|--------|------|
| mypy | `make lint-types` | Typ-Check aller Python-Module |
| ruff | `make lint-style` | Linting und Code-Qualität |
| bandit | `make security` | Sicherheits-Scans |
| vulture | — | Dead-Code-Erkennung (optional) |

### 2. Unit-Tests (aktuell: 111)

Jedes Modul wird isoliert getestet. Externe Abhängigkeiten werden gemockt.

| Modul | Tests | Coverage-Ziel |
|-------|-------|---------------|
| `darknet_search/` | 6 | ≥ 90 % |
| `search/` | 12 | ≥ 90 % |
| `vectordb/` | 6 | ≥ 90 % |
| `onion_discovery/` | 26 | ≥ 85 % |
| `crawlers/` | 0 | ≥ 80 % (geplant) |
| `config/` | 8 | ≥ 95 % |
| `mcp_tools/` | 25 | ≥ 85 % |
| `dashboard/` | 11 | ≥ 80 % |
| **Gesamt** | **111** | **≥ 85 %** |

### 3. Integrationstests

Testen das Zusammenspiel mehrerer Module mit gemockten externen Diensten.

- CompositeRetriever + Whoosh + SearXNG (gemockt)
- Onion Discovery Pipeline + PolicyGateway + ReviewQueue
- ChromaDB + EmbeddingService (echte ChromaDB-Instanz)
- MCP-Tools + bestehende Services

### 4. Playwright-Visual-Tests

```bash
# Setup
playwright install chromium

# Tests ausführen
python -m pytest tests/playwright/ -v

# Screenshot-Vergleich (Baseline)
python -m pytest tests/playwright/ --screenshot-base
# Vergleich
python -m pytest tests/playwright/ --screenshot-diff
```

Geplante Visual-Tests:

- **Dashboard (T-017):** GPU-Auslastung, VRAM-Balken, Warmmeldungen
- **GPT-Researcher UI:** Startseite, Recherche-Formular, Report-Ansicht
- **Accessibility:** Kontraste, ARIA-Labels, Tastatur-Navigation

### 5. E2E-Tests (mit laufenden Diensten)

Voraussetzung: Ollama + SearXNG + ChromaDB + Tor laufen.

- **Szenario 1:** Vollständige Recherche mit CompositeRetriever
- **Szenario 2:** Onion-Discovery-Durchlauf
- **Szenario 3:** Dashboard + GPU-Daten
- **Szenario 4:** Human-Review → Indexierung
- **Szenario 5:** Fehlertoleranz (SearXNG down)

## Befehle

### Vollständige Testsuite

```bash
./scripts/run-all-tests.sh
```

### Einzelne Bereiche

```bash
make test         # pytest
make coverage     # pytest --cov
make lint         # ruff check
make lint-types   # mypy
make security     # bandit
make playwright   # playwright tests
make all          # Alles oben
```

## Coverage-Reporting

```bash
pytest --cov --cov-report=html --cov-report=xml
```

Reports:
- HTML: `coverage_html/index.html`
- XML: `coverage.xml` (CI-kompatibel)

### Aktuelle Coverage (Schwellenwerte)

```ini
# pyproject.toml
[tool.coverage.report]
fail_under = 85
```

## Playwright-Integration

### Setup

```bash
pip install playwright
playwright install chromium
```

### Test-Struktur

```
tests/playwright/
├── conftest.py           # Playwright-Fixtures
├── test_dashboard.py     # Dashboard-Visual-Tests
└── screenshots/
    ├── baseline/         # Referenz-Screenshots
    └── diff/             # Abweichungen bei Regression
```

### Screenshot-Vergleich

1. `make playwright-baseline` — erstellt Baseline-Screenshots
2. `make playwright-test` — vergleicht aktuelle mit Baseline
3. Bei Regression: Screenshot-Diff in `screenshots/diff/`

## CI-Integration (geplant)

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: make all
```

## Offene Punkte (⏳)

- [ ] Playwright-Visual-Tests für Dashboard implementieren
- [ ] E2E-Szenarien 1-5 als automatisierte Tests
- [ ] CI-Pipeline (GitHub Actions)
- [ ] Crawler-Unit-Tests (HTTP-Error-Simulation)
- [ ] Benchmarking: Query-Latenz p50/p95 für Whoosh-Index
