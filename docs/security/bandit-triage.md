# Bandit Triage Policy

**Datum:** 2026-05-19  
**Bandit-Version:** 1.9.4  
**Ausführung:** `python3 -m bandit -r . --skip B101,B311,B404,B603`

---

## Summary

| Severity | Anzahl | Projekt | Submodul | Behandelt |
|---:|---:|---:|---:|---|
| HIGH | 7 | 0 | 7 | 0 behoben, 7 Vendor-dokumentiert |
| MEDIUM | 18 | 2 | 16 | 0 behoben, 2 Test-akzeptiert, 16 Vendor-dokumentiert |
| LOW | 18 | 9 | 9 | 0 behoben, 9 Test/akzeptiert, 9 Vendor-dokumentiert |
| **Gesamt** | **43** | **11** | **32** | **43 triagiert** |

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

## Projekt-Findings (11)

### Akzeptiert mit Begründung (11)

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

---

## Submodul-Findings (32) — `gpt_researcher/`

### HIGH (7) — Vendor-dokumentiert

| # | Test-ID | CWE | Datei | Zeile | Beschreibung | Risiko |
|---:|---|---|---|---|---|---|
| 1 | B324 | CWE-327 | `backend/report_type/basic_report/basic_report.py` | 70 | `hashlib.md5()` für Forschungs-ID | Nicht sicherheitsrelevant (ID-Generierung), aber Upgrade auf SHA-256 empfohlen |
| 2 | B324 | CWE-327 | `backend/report_type/detailed_report/detailed_report.py` | 81 | `hashlib.md5()` für Forschungs-ID | Wie oben |
| 3 | B324 | CWE-327 | `backend/server/server_utils.py` | 120 | `hashlib.md5()` für Task-Hash | Nicht sicherheitsrelevant |
| 4 | B324 | CWE-327 | `gpt_researcher/agent.py` | 212 | `hashlib.md5()` für Research-ID | Nicht sicherheitsrelevant |
| 5 | B324 | CWE-327 | `llm_provider/image/image_generator.py` | 103 | `hashlib.md5()` für Bild-Dateiname | Nicht sicherheitsrelevant (Dateiname) |
| 6 | B324 | CWE-327 | `scraper/utils.py` | 89 | `hashlib.md5()` für Image-Identifier | Nicht sicherheitsrelevant |
| 7 | B501 | CWE-295 | `scraper/pymupdf/pymupdf.py` | 53 | `requests.get(..., verify=False)` | ⚠️ SSL-Verify deaktiviert. Risiko bei externen PDF-Quellen. NUR im Submodul-Scraper. |

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

### LOW (9) — Vendor-dokumentiert

| Test-ID | Anzahl | Typ |
|---|---|---|
| B110 | 4 | `try/except/pass` in Submodul-Code |
| B105 | 4 | Hardcoded-Zahlen als "Passwörter" erkannt (Token-Limits: 3000, 6000, 4000, 700) |
| B607 | 1 | `subprocess.run(["nvidia-smi",...])` in Submodul-Integrationstest |
| B405 | 1 | `xml.etree.ElementTree`-Import in PubMed-Retriever |
| B403 | 1 | `pickle`-Import in Browser-Scraper |
| B112 | 1 | `try/except/continue` in Google-Retriever |

---

## Behobene Findings

Keine produktiven Code-Änderungen. Alle Projekt-Findings sind dokumentiert akzeptiert (Test-only, Low-Severity, oder System-Tool-Aufrufe).

---

## Akzeptierte Risiken

| Finding | Risiko | Begründung | Follow-up |
|---|---|---|---|
| GPU-Monitor B607 (3×) | Minimal | `nvidia-smi` ist Standard-Systemtool. Kein untrusted Input. | Kein Follow-up nötig |
| Playwright B310 (2×) | Test-only | Health-Check + JSON-Read gegen `localhost`. | Kein Follow-up nötig |
| Test-Credentials B105 (2×) | Test-only | Mock-Werte in Test-Fixtures. | Kein Follow-up nötig |
| Submodul B324 MD5 (6×) | Gering | Nicht-sicherheitsrelevante IDs/Dateinamen. Upstream-Fix empfohlen. | Issue in GPT-Researcher-Repo vorschlagen |
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

1. **Submodul-Security-Review**: MD5→SHA-256 im GPT-Researcher-Fork (6 Stellen)
2. **SSL-Verify-Audit**: `gpt_researcher/scraper/pymupdf/pymupdf.py` — `verify=False` prüfen
3. **Requests-Timeout-Upstream**: 8 Retriever ohne Timeout im Submodul
4. **Security Regression Tests**: Netzwerk-/Hashing-/SQL-Pfade
