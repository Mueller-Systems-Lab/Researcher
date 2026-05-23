# Test Profiles

**Datum:** 2026-05-19  
**Scope:** Researcher Test- und Quality-Gate-Profile  

---

## Ziel

Klare Trennung von schnellen Entwickler-Checks und vollständigen CI-Läufen.

---

## Profile

| Target | Zweck | Lokal | CI | Zeit |
|---|---|---|---|---|
| `test-fast` | Unit/Integration ohne schwere Tests | ✅ | ✅ | ~15s |
| `test-e2e` | E2E-Pipeline-Tests | ✅ | ✅ | <1s |
| `test-benchmarks` | Performance-Benchmarks | 🔧 | 📋 | ~3min |
| `quality` | lint + typecheck + security + test-fast | ✅ | ✅ | ~30s |
| `coverage` | Coverage-Gate (≥78%) | ✅ | ✅ | ~10s |
| `ci-local` | quality + coverage + e2e | ✅ | ✅ | ~45s |
| `ci-full` | alles inkl. benchmarks + reports | 🔧 | 📋 | ~5min |

## Lokaler Standardworkflow

```bash
# Schneller Check nach Änderung
make quality

# Coverage prüfen
make coverage

# E2E-Stabilität
make test-e2e
```

## Vollständiger CI-Lauf

```bash
# Lokal:
make ci-local

# Komplett (inkl. Benchmarks):
make ci-full
```

---

## Langsame Tests

### Benchmarks (`make test-benchmarks`)
- `tests/benchmarks/` — Whoosh vs SQLite FTS5 (100 + 1000 docs)
- 300s Timeout per conftest
- Optional für PRs, empfohlen für nightly/scheduled CI

### Playwright (`make playwright`)
- `tests/playwright/` — Visual Regression + Accessibility
- Benötigt Playwright + Chromium
- Optional, separat ausführbar

---

## Security-Reports

```bash
make security-report    # JSON + TXT in reports/
make security-vendor    # Vendor-Code Scan (report-only)
make security-project   # Projekt-Code Scan (blocking)
```

---

## Wann welches Profil?

| Situation | Profil |
|---|---|
| Nach Code-Änderung | `make quality` |
| Vor Commit/Push | `make ci-local` |
| PR-Review | CI: `quality` + `coverage` + `test-e2e` |
| Nightly/Scheduled | `ci-full` + `make playwright` |
| Performance-Regression | `make test-benchmarks` |

---

## Bekannte Grenzen

- `make test-fast` ignoriert: benchmarks, e2e, playwright-accessibility, playwright-visual-regression
- `make coverage` verwendet denselben Ignore-Set wie `test-fast`
- `make ci-full` beinhaltet Benchmarks (~3min) und Security-Reports
- Playwright-Tests benötigen `playwright install chromium`
