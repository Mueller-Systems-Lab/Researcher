# Typecheck Policy

**Datum:** 2026-05-19  
**Scope:** mypy Typechecking für Researcher  

---

## Ziel

Definiert, wie mypy-Typechecking für Projekt- und Vendor-Code getrennt behandelt wird.

---

## Scope

### Projekt-eigener Code (eigener Typecheck)
```
config/  crawlers/  darknet_search/  search/  dashboard/
vectordb/  mcp_tools/  onion_discovery/  scripts/
```

### Vendor-/Submodul-Bereich (separater Typecheck)
```
gpt_researcher/
```

---

## Blocking Rules

| Bereich | Blocking | Begründung |
|---|---|---|
| Projektcode | ⚠️ Non-blocking (aktuell) | 33 bekannte Type-Errors, Folge-Issue geplant |
| Projektcode | 🎯 Blocking (Ziel) | Nach Behebung der 33 Errors |
| Vendor/Submodul | 📋 Report-only | Submodul-Code, 1 bekannter `ports`-Duplicate-Error |
| Tests | 📋 Nicht im Scope | `tests/` separat zu behandeln |

---

## Makefile Targets

| Target | Beschreibung | Status |
|---|---|---|
| `make lint-types` | Full-Repo mypy (Legacy, bleibt) | Non-blocking (`\|\| true`) |
| `make typecheck` | Nur Projektcode | ⚠️ Non-blocking (33 Errors) |
| `make typecheck-vendor` | Nur Submodul | 📋 Report-only |

---

## Bekannte Type-Errors

### Projektcode (33 Errors, 12 Dateien)
| Datei | Errors | Typ |
|---|---|---|
| `scripts/uncensored_research.py` | >10 | `object` nicht indexierbar |
| `mcp_tools/claim_validator.py` | 2 | Fehlende Type-Annotation |
| `scripts/patch_gpt_researcher.py` | 1 | Cannot assign to a type |
| Weitere 9 Dateien | ~20 | Verschiedene type-issues |

**Geplanter Fix:** Folge-Issue — Batch-Fix der 33 Type-Errors vor Aktivierung des blocking Gates.

### Vendor-Code (1 Error)
- `gpt_researcher/ports/search_index_repository.py`: Duplicate module "ports.search_index_repository" vs "gpt_researcher.ports.search_index_repository"
- Ursache: Submodul-Namespace-Konflikt
- Fix: `__init__.py` in `gpt_researcher/ports/` oder `--explicit-package-bases`

---

## CI-Verhalten

### test.yml
```yaml
- name: Type check (mypy)
  run: make lint-types || true

- name: Typecheck project code
  run: make typecheck

- name: Typecheck vendor code
  run: make typecheck-vendor
```

Alle drei Steps sind non-blocking (`|| true`), bis Projekt-Type-Errors behoben sind.

---

## pyproject.toml

```toml
[tool.mypy]
ignore_missing_imports = true
warn_return_any = false
warn_unused_configs = true
no_implicit_optional = true

[[tool.mypy.overrides]]
module = ["gpt_researcher.*"]
ignore_errors = true
```

---

## Warum kein globales ignore_errors?

Globales `ignore_errors = true` würde ALLE Type-Errors unsichtbar machen. Das ist nicht das Ziel. Stattdessen:
1. Vendor-Code per `[[tool.mypy.overrides]]` ausgeklammert
2. Projekt-Code separat gecheckt (aktuell non-blocking wegen 33 Errors)
3. Ziel: blocking nach Behebung der Errors

---

## Konsistenz mit anderen Gates

| Gate | Projekt blockierend | Vendor report-only | Issue |
|---|---|---|---|
| ruff | ✅ Ja (0 Errors) | ✅ Excluded | #51 |
| bandit | ✅ Ja (0 Medium/High) | ✅ report-only | #54 |
| mypy | 🎯 Ziel | ✅ report-only | #55 (dieses) |
| tests | ✅ Ja | N/A | #50 |
| coverage | ✅ Ja (≥78%) | N/A | #50 |

---

## Folge-Issues

1. **33 Projekt-Type-Errors beheben** — Voraussetzung für blocking `make typecheck`
2. **Vendor `ports`-Duplicate fixen** — `__init__.py` oder `--explicit-package-bases`
3. **Typing-Coverage messen** — `mypy --strict` als Ziel definieren
