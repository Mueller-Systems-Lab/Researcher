# Changelog – Iteration 2

## Metadaten

- **Datum:** 2026-05-17
- **Typ:** Codebase Audit + Repair Cycle
- **Bereich:** Security, Qualität, Wartung, Testabdeckung, Dokumentation

## Audit-Zusammenfassung

- **Gefundene Issues:** 8
- **Behoben:** 8
- **Regressions:** 0
- **Tests:** 173 bestanden (170 Unit/Integration + 3 Playwright)
- **Tech Debt Score:** 0 critical / 0 high / 0 medium / 0 low

## Behobene Issues

| Issue | Bereich | Änderung |
|---|---|---|
| #30 | Security | `darknet_search/index.py`: `hash()` für Dokument-IDs durch `hashlib.sha256()` ersetzt. |
| #31 | Qualität | `onion_discovery/__main__.py`: Zugriff auf privates `rq._items` durch `ReviewQueue.get_pending_items()` ersetzt. |
| #32 | Qualität | Echte Playwright-Browsertests ergänzt: `tests/playwright/test_dashboard_visual_regression.py`. |
| #33 | Qualität | `vectordb/store.py`: `query()`-Docstring präzisiert, `where_filter` ergänzt. |
| #34 | Wartung | `onion_discovery/seed_queue.py`: `auto_save=False` eingeführt, Batch-Saves in `add_seeds()`. |
| #35 | Wartung | ADR für Whoosh-Ablösung erstellt: `docs/adr/ADR-014-whoosh-migration.md`. |
| #36 | Wartung | Trunkierte `md5`-IDs in `retriever.py`, `engine.py`, `human_review.py` auf `sha256()` umgestellt. |
| #37 | Wartung | Produktionsweite `except Exception`-Blöcke mit `exc_info=True` / `logger.exception()` verbessert. |

## Neue Artefakte

- `docs/adr/ADR-014-whoosh-migration.md` — ADR zur Migration von Whoosh zu SQLite FTS5 (renamed)
- `tests/playwright/test_dashboard_visual_regression.py` — 3 echte Playwright-Tests
- `tests/playwright/baselines/dashboard_visual_regression.png` — Visual-Baseline für das Dashboard

## Ergebnis

Die Audit-Fixes wurden vollständig umgesetzt, ohne Regressionen einzuführen. Die Browser-Tests decken jetzt Dashboard-Load, SSE-Stream und visuelle Regression ab. Die Whoosh-Nutzung ist weiterhin dokumentiert, aber als Migrationsrisiko mit ADR-Planung versehen.

## Status

- Dokumentation der Audit- und Repair-Iteration abgeschlossen.
- Nächster sinnvoller Schritt: Migration von Whoosh gemäß ADR-008 planen und umsetzen.
