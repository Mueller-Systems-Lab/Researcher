# Security Gate Policy

**Datum:** 2026-05-27  
**Version:** 1.1  
**Scope:** Researcher CI/CD Security Gates  

---

## Ziel

Definiert, welche Bandit-Security-Findings in welchem Code-Bereich blockierend sind und welche als dokumentierte Ausnahmen akzeptiert werden.

---

## Scope

### Projekt-eigener Code (strenger Scan)
```
config/  crawlers/  darknet_search/  search/  dashboard/
vectordb/  mcp_tools/  onion_discovery/  scripts/
```

### Vendor-/Submodul-Bereich (dokumentierter Scan)
```
gpt_researcher/
```

### Reports (CI-Artefakte)
```
reports/bandit-full.json
reports/bandit-full.txt
```

---

## Blocking Rules

| Bereich | Severity | Blocking | Begründung |
|---|---|---|---|
| Projektcode | High | ✅ Ja | Sicherheitskritisch, muss sofort behoben werden |
| Projektcode | Medium | ✅ Ja | Erhöhtes Risiko, soll vor Merge behoben sein |
| Projektcode | Low | ⚠️ Review | Dokumentieren, triagieren, nicht blind blockieren |
| Vendor-Code | High | 📋 Report-only | Submodul-Fork, Änderungen nur mit eigenem Review |
| Vendor-Code | Medium | 📋 Report-only | Wie oben |
| Vendor-Code | Low | 📋 Report-only | Wie oben |
| Tests (Projekt) | Alle | 📋 Review | Test-Code, separate Prüfung |

---

## Makefile Targets

| Target | Beschreibung | Blocking |
|---|---|---|
| `make security` | Full-Repo-Bandit-Scan | Nein (Report) |
| `make security-project` | Nur Projektcode, ab Medium | ✅ Ja |
| `make security-vendor` | Nur Submodul | Nein (`\|\| true`) |
| `make security-report` | JSON + TXT Reports | Nein |

---

## CI-Verhalten

### test.yml (bestehend)
- `make lint` — blocking (0 Errors erwartet)
- `make lint-types` — non-blocking (`|| true`)
- `make security` — non-blocking (`|| true`)
- `make security-project` — jetzt ✅ grün (0 Medium+ Findings)
- `make coverage` — blocking (≥78%)

### Empfohlene CI-Ergänzung (für Artefakt-Upload)
```yaml
- name: Security scan project code
  run: make security-project

- name: Security report full repository
  run: make security-report

- name: Upload security reports
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: bandit-security-reports
    path: reports/bandit-*.*
```

---

## Baseline-Verhalten

Keine Bandit-Baseline-Datei verwendet. Stattdessen:
1. Vendor-Code über `make security-vendor` separat gescannt (non-blocking)
2. Projekt-Code über `make security-project` streng geprüft (blocking ab Medium)
3. Alle Findings in `docs/security/` dokumentiert

---

## Bekannte akzeptierte Findings

Siehe:
- `docs/security/bandit-triage.md` — Vollständige Triage (43 Findings)
- `docs/security/submodule-security-review.md` — Submodul-Fixes (14/15)

### Projektcode (alle akzeptiert)
| ID | Typ | Begründung |
|---|---|---|
| B607 | nvidia-smi Partial-Path | Standard-Systemtool, GPU-Monitor optional |
| B310 | urlopen in Playwright + local_llm_runtime | Test-only + Scheme via _validate_url_scheme geprüft |
| B314 | ET.parse in classify-errors.py | defusedxml verwendet, Fallback nur CI-JUnit-XML |
| B105 | Test-Credentials | Mock-Werte in Test-Fixtures |

### Submodul (nach Fixes)
| ID | Vorher | Nachher | Status |
|---:|---:|---:|---|
| B324 (MD5) | 6 | 0 | Gefixt |
| B113 (Timeout) | 8 | 0 | Gefixt |
| B501 (SSL) | 1 | 1 | Akzeptiert (Fallback) |
| Sonstige | 17 | 19 | Vendor-dokumentiert |

---

## Regression-Regeln

1. **Neue Projekt-High-Findings**: CI muss fehlschlagen
2. **Neue Projekt-Medium-Findings**: CI muss fehlschlagen
3. **Neue Vendor-High-Findings**: Sichtbar in `make security-report`, Review-Pflicht
4. **Bestehende Vendor-Findings**: In Doku referenziert, kein CI-Fail

---

## Folge-Issues

1. `make security-project` High-Findings analysieren und triagieren
2. Submodul-Findings weiter reduzieren (Upstream-PR)
3. Security-Regression-Tests für Netzwerk-Timeouts
4. `reports/` zu `.gitignore` hinzufügen
