# Bandit Triage Policy

**Datum:** 2026-06-05  
**Bandit-Version:** 1.9.4  
**Ausführung:** `python3 -m bandit -r . --skip B101,B311,B404,B603`

---

## Summary

| Severity | Anzahl | Projekt | Submodul | Behandelt |
|---:|---:|---:|---:|---|
| HIGH | 8 | 0 | 8 | 0 behoben, 8 Vendor-dokumentiert |
| MEDIUM | 16 | 0 | 16 | Projekt-Gate grün, 16 Vendor-dokumentiert |
| LOW | 20 | 9 | 11 | 9 Projekt-akzeptiert, 11 Vendor-dokumentiert |
| **Gesamt** | **44** | **9** | **35** | **44 triagiert** |

---

## Scope

### Projekt-eigener Code (auditiert + triagiert)
- `config/`, `crawlers/`, `darknet_search/`, `search/`, `dashboard/`
- `vectordb/`, `mcp_tools/`, `onion_discovery/`, `scripts/`
- `tests/`, `infra/`

### Vendor-/Submodul-Bereich (dokumentiert, nicht modifiziert)
- `gpt_researcher/` — GPT Researcher v0.14.8 Fork
- Keine Änderungen am Submodul-Code ohne explizite Begründung

---

## Projekt-Findings

### Aktueller Projekt-Gate-Run — 2026-06-05

```text
$ make security-project
python3 -m bandit -r config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts --skip B101,B311,B404,B603 --severity-level medium
Test results:
    No issues identified.
Run metrics:
    Total issues (by severity): Low: 9, Medium: 0, High: 0
    Total potential issues skipped due to specifically being disabled: 8
```

Ergebnis: **0 Medium/High-Findings im Projekt-Gate**. Zwei bereits dokumentierte
`scripts/visual_e2e_acceptance.py`-B310-Akzeptanzen sind jetzt zusätzlich mit
`# nosec B310` markiert, weil beide Aufrufe auf fest verdrahtete
`127.0.0.1`-URLs mit explizitem Timeout beschränkt sind.

### Historisch akzeptiert mit Begründung (14)

| # | Test-ID | Severity | Datei | Zeile | Begründung |
|---:|---|---|---|---|---|
| 1 | B607 | LOW | `dashboard/gpu_monitor.py` | 57 | `subprocess.run(["nvidia-smi",...])`: Standard-Systemtool. Kein untrusted Input. GPU-Monitor läuft optional. |
| 2 | B607 | LOW | `dashboard/gpu_monitor.py` | 110 | `subprocess.run(["nvidia-smi",...])`: Wie oben. |
| 3 | B607 | LOW | `dashboard/gpu_monitor.py` | 165 | `subprocess.run(["which","nvidia-smi"])`: Wie oben. |
| 4 | B607 | LOW | `infra/integration_test.py` | 24 | Infra-Testskript. Kein Produktivcode. |
| 5 | B110 | LOW | `infra/test_embeddings.py` | 57 | Infra-Testskript: `try/except/pass` in Test-Utility. |
| 6 | B310 | MEDIUM | `tests/playwright/test_dashboard_visual_regression.py` | 61 | Playwright-Test: `urllib.request.urlopen` für Health-Check gegen `localhost`. Test-only, kein untrusted Input. |
| 7 | B310 | MEDIUM | `tests/playwright/test_dashboard_visual_regression.py` | 95 | Playwright-Test: `urllib.request.urlopen` für JSON-Read. Test-only. |
| 8 | B105 | LOW | `tests/test_crawlers.py` | 55 | Test-Fixture: `crawler.config.password = ""`. Test-only, kein Produktiv-Credential. |
| 9 | B105 | LOW | `tests/test_crawlers.py` | 179 | Test-Assertion: `assert token == "abc123"`. Mock-Testwert, kein Produktiv-Token. |
| 10 | B310 | MEDIUM | `scripts/visual_e2e_acceptance.py` | 153 | Acceptance-Skript (pre-existing): `urllib.request.urlopen` für SearXNG-Healthcheck. URLs sind hardcoded `http://127.0.0.1:*`. Kein untrusted Input. |
| 11 | B310 | MEDIUM | `scripts/visual_e2e_acceptance.py` | 194 | Acceptance-Skript (pre-existing): `urllib.request.urlopen` für API-Reports-Check. URL ist hardcoded `http://127.0.0.1:28202`. |
| 12 | B310 | MEDIUM | `scripts/ci_acceptance.py` | 72 | Phase 8 CI-Acceptance: `urllib.request.urlopen` via `_validate_url_scheme()`. URLs hardcoded auf `127.0.0.1`. Defense-in-depth durch URL-Validierung. |
| 13 | B310 | MEDIUM | `scripts/ci_acceptance.py` | 117 | Wie oben — `_submit()`-Pfad, `_validate_url_scheme()` validiert. |
| 14 | B310 | MEDIUM | `scripts/ci_acceptance.py` | 127 | Wie oben — `_wait_for_completion()`-Pfad, `_validate_url_scheme()` validiert. |

---

## Submodul-Findings (35) — `gpt_researcher/`

### Aktueller Vendor-Scan — 2026-06-05

```text
$ python3 -m bandit -r gpt_researcher --skip B101,B311,B404,B603
Run metrics:
    Total issues (by severity): Low: 11, Medium: 16, High: 8
```

Ergebnis: **report-only, nicht blockierend**. Seit der letzten Triage gibt es ein
neues Vendor-High-Finding: `B324` in
`gpt_researcher/gpt_researcher/llm_provider/image/modelslab_image_generator.py:64`
(`hashlib.md5()` für Bild-Dateiname). Akzeptanz wie bei den bestehenden
MD5-Findings: nicht für Sicherheitsentscheidungen genutzt, aber Upstream-/Fork-Fix
auf SHA-256 oder `usedforsecurity=False` empfohlen.

### HIGH (8) — Vendor-dokumentiert

| # | Test-ID | CWE | Datei | Zeile | Beschreibung | Risiko |
|---:|---|---|---|---|---|---|
| 1 | B324 | CWE-327 | `backend/report_type/basic_report/basic_report.py` | 70 | `hashlib.md5()` für Forschungs-ID | Nicht sicherheitsrelevant (ID-Generierung), aber Upgrade auf SHA-256 empfohlen |
| 2 | B324 | CWE-327 | `backend/report_type/detailed_report/detailed_report.py` | 81 | `hashlib.md5()` für Forschungs-ID | Wie oben |
| 3 | B324 | CWE-327 | `backend/server/server_utils.py` | 120 | `hashlib.md5()` für Task-Hash | Nicht sicherheitsrelevant |
| 4 | B324 | CWE-327 | `gpt_researcher/agent.py` | 212 | `hashlib.md5()` für Research-ID | Nicht sicherheitsrelevant |
| 5 | B324 | CWE-327 | `llm_provider/image/image_generator.py` | 103 | `hashlib.md5()` für Bild-Dateiname | Nicht sicherheitsrelevant (Dateiname) |
| 6 | B324 | CWE-327 | `llm_provider/image/modelslab_image_generator.py` | 64 | `hashlib.md5()` für Bild-Dateiname | Nicht sicherheitsrelevant (Dateiname) |
| 7 | B324 | CWE-327 | `scraper/utils.py` | 89 | `hashlib.md5()` für Image-Identifier | Nicht sicherheitsrelevant |
| 8 | B501 | CWE-295 | `scraper/pymupdf/pymupdf.py` | 52 | `requests.get(..., verify=False)` | ⚠️ SSL-Verify deaktiviert. Risiko bei externen PDF-Quellen. NUR im Submodul-Scraper. |

### MEDIUM (16) — Vendor-dokumentiert

| Test-ID | Anzahl | Beschreibung | Risiko-Einschätzung |
|---|---|---|---|
| B113 | 8 | `requests.*` ohne Timeout (SearXNG, Bing, Bocha, Custom, Google, PubMed, Semantic Scholar) | Submodul-Retriever. Timeout sollte upstream ergänzt werden. |
| B608 | 2 | SQL-String-Konstruktion (MCP-Tool-Selector-Logs) | **False Positive**: Nur Logger-Ausgaben, keine SQL-Ausführung. |
| B104 | 2 | `uvicorn.run(host="0.0.0.0")` | Submodul-Server. Lokale Entwicklung, kein Produktiv-Deployment. |
| B310 | 1 | `urllib.request.urlopen` in Xquik-Retriever | Submodul. Sollte `requests` mit Timeout verwenden. |
| B314 | 1 | `xml.etree.ElementTree.fromstring` in PubMed-Retriever | Submodul. XML-Parsing von externen Quellen. |
| B301 | 1 | `pickle.load` in Browser-Scraper | Submodul. Cookie-Persistenz. |
| B108 | 1 | Hardcoded `/tmp` in Submodul-Test | Test-only im Submodul. |

### LOW (11) — Vendor-dokumentiert

| Test-ID | Anzahl | Typ |
|---|---|---|
| B110 | 4 | `try/except/pass` in Submodul-Code |
| B105 | 4 | Hardcoded-Zahlen als "Passwörter" erkannt (Token-Limits: 3000, 6000, 4000, 700) |
| B405 | 1 | `xml.etree.ElementTree`-Import in PubMed-Retriever |
| B403 | 1 | `pickle`-Import in Browser-Scraper |
| B112 | 1 | `try/except/continue` in Google-Retriever |

---

## Behobene Findings

- `scripts/visual_e2e_acceptance.py`: Zwei lokal fest verdrahtete B310-Healthcheck-Aufrufe sind nach erneuter Prüfung mit `# nosec B310` markiert. Beide verwenden explizite Timeouts und ausschließlich `127.0.0.1`-Ziele.
- `scrapers/http_session.py`: SSL- und User-Agent-Fallback-GETs setzen jetzt auch dann einen expliziten Timeout, wenn der Aufrufer keinen Timeout in `kwargs` übergibt.
- Neue Regressionstests unter `tests/security/test_network_timeout_regression.py` sichern Timeout-Handling und statische Timeout-Verwendung in Projekt-HTTP-Aufrufen ab.

---

## Akzeptierte Risiken

| Finding | Risiko | Begründung | Follow-up |
|---|---|---|---|
| GPU-Monitor B607 (3×) | Minimal | `nvidia-smi` ist Standard-Systemtool. Kein untrusted Input. | Kein Follow-up nötig |
| Playwright B310 (2×) | Test-only | Health-Check + JSON-Read gegen `localhost`. | Kein Follow-up nötig |
| Test-Credentials B105 (2×) | Test-only | Mock-Werte in Test-Fixtures. | Kein Follow-up nötig |
| Submodul B324 MD5 (7×) | Gering | Nicht-sicherheitsrelevante IDs/Dateinamen. Upstream-Fix empfohlen. | Issue in GPT-Researcher-Repo vorschlagen |
| Submodul B501 SSL-Verify | ⚠️ Mittel | `verify=False` im PDF-Scraper. Nur relevant bei externen PDFs. | Bei Fork-Update prüfen |

---

## CI-Gate-Empfehlung

`make security` kann als **non-blocking warning step** in CI verwendet werden:

```yaml
- name: Security (bandit)
  run: make security || true
```

Für blockierendes Gate: Bandit-Baseline erstellen, die nur Projekt-eigene Dateien scannt:

```bash
python3 -m bandit -r config crawlers darknet_search search dashboard \
  vectordb mcp_tools onion_discovery scripts tests infra \
  --skip B101,B311,B404,B603
```

**Empfehlung:** Baseline erstellen, wenn Submodul-Findings im Fork behoben wurden.

---

## Nächste Security-Issues

1. **Submodul-Security-Review**: MD5→SHA-256 im GPT-Researcher-Fork (7 Stellen)
2. **SSL-Verify-Audit**: `gpt_researcher/scraper/pymupdf/pymupdf.py` — `verify=False` prüfen
3. **Requests-Timeout-Upstream**: 8 Retriever ohne Timeout im Submodul
4. **Security Regression Tests**: Netzwerk-/Hashing-/SQL-Pfade
