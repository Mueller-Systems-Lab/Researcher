# Submodule Security Review — gpt_researcher

**Datum:** 2026-05-19  
**Scope:** `gpt_researcher/` Submodul (GPT Researcher v0.14.8 Fork)  
**Basis:** Issue #52 (Bandit Triage), #53 (diese Review)  

---

## Stand

Bandit 1.9.4 Scan des Submoduls vor Review: **32 Findings** (7 High, 18 Medium, 7 Low).  
Nach Review-Maßnahmen: Fixes dokumentiert, keine Regression.

---

## Findings Summary

| Kategorie | Anzahl | Entscheidung | Behandelt |
|---:|---|---|
| MD5/SHA (B324) | 6 | `usedforsecurity=False` | ✅ 6/6 gefixt |
| Requests-Timeout (B113) | 8 | `timeout=(5,30)` ergänzt | ✅ 8/8 gefixt |
| SSL-Verify (B501) | 1 | Akzeptiert (Fallback-Pattern) | ✅ Dokumentiert |
| Sonstige (B104/110/112/301/310/314/403/405/608) | 17 | Vendor-dokumentiert | ✅ In #52 dokumentiert |

---

## MD5/SHA Findings

Alle 6 MD5-Verwendungen sind **nicht-sicherheitsrelevant** (Research-IDs, Task-Hashes, Image-Dateinamen, Cache-Keys).

| Datei | Zeile | Entscheidung | Begründung | Risiko |
|---|---|---|---|---|
| `backend/report_type/basic_report/basic_report.py` | 70 | FIXED | Research-ID, kein Security-Kontext | Kein |
| `backend/report_type/detailed_report/detailed_report.py` | 81 | FIXED | Research-ID, kein Security-Kontext | Kein |
| `backend/server/server_utils.py` | 120 | FIXED | Task-Hash für Dateiname, kein Security-Kontext | Kein |
| `gpt_researcher/agent.py` | 212 | FIXED | Research-ID, kein Security-Kontext | Kein |
| `llm_provider/image/image_generator.py` | 103 | FIXED | Image-Dateiname, kein Security-Kontext | Kein |
| `scraper/utils.py` | 89 | FIXED | Image-Cache-Key, kein Security-Kontext | Kein |

**Fix:** `hashlib.md5(..., usedforsecurity=False)` + `# noqa: B324` Kommentar.

---

## Requests Timeout Findings

8 Retriever ohne explizites Timeout. Alle mit `timeout=(5, 30)` ergänzt (PubMed fetch: `(5, 60)` wegen PDF-Download).

| Datei | Zeile | Typ | Timeout |
|---|---|---|---|
| `retrievers/semantic_scholar/semantic_scholar.py` | 39 | GET | `(5, 30)` |
| `retrievers/custom/custom.py` | 48 | GET | `(5, 30)` |
| `retrievers/bing/bing.py` | 67 | GET | `(5, 30)` |
| `retrievers/bocha/bocha.py` | 42 | POST | `(5, 30)` |
| `retrievers/google/google.py` | 69 | GET | `(5, 30)` |
| `retrievers/searx/searx.py` | 58 | GET | `(5, 30)` |
| `retrievers/pubmed_central/pubmed_central.py` | 62 | GET (search) | `(5, 30)` |
| `retrievers/pubmed_central/pubmed_central.py` | 87 | GET (fetch) | `(5, 60)` |

---

## SSL Verify Findings

| Datei | Zeile | Entscheidung | Begründung | Risiko |
|---|---|---|---|---|
| `scraper/pymupdf/pymupdf.py` | 53 | AKZEPTIERT | `verify=False` nur als Fallback nach SSLError. Erstversuch mit Default-Verify. | Gering — Pattern: try-first, fallback-on-error mit Log-Warnung |

**Code-Flow:**  
1. `requests.get(url, timeout=(5,30), stream=True)` → Standard-Verify  
2. Bei `SSLError`: Log-Warnung → `requests.get(url, verify=False)` als Fallback

Dieses Pattern ist für einen PDF-Scraper angemessen (Self-Signed-Certs auf Zielseiten).

---

## Geänderte Stellen (14 Dateien)

### MD5-Fixes (6)
- `gpt_researcher/backend/report_type/basic_report/basic_report.py` — line 70
- `gpt_researcher/backend/report_type/detailed_report/detailed_report.py` — line 81
- `gpt_researcher/backend/server/server_utils.py` — line 120
- `gpt_researcher/gpt_researcher/agent.py` — line 212
- `gpt_researcher/gpt_researcher/llm_provider/image/image_generator.py` — line 103
- `gpt_researcher/gpt_researcher/scraper/utils.py` — line 89

### Requests-Timeout (8)
- `gpt_researcher/gpt_researcher/retrievers/semantic_scholar/semantic_scholar.py` — line 39
- `gpt_researcher/gpt_researcher/retrievers/custom/custom.py` — line 48
- `gpt_researcher/gpt_researcher/retrievers/bing/bing.py` — line 67
- `gpt_researcher/gpt_researcher/retrievers/bocha/bocha.py` — line 42
- `gpt_researcher/gpt_researcher/retrievers/google/google.py` — line 69
- `gpt_researcher/gpt_researcher/retrievers/searx/searx.py` — line 58
- `gpt_researcher/gpt_researcher/retrievers/pubmed_central/pubmed_central.py` — lines 62, 87

---

## Nicht geänderte Stellen (17)

Alle sonstigen Submodul-Findings aus #52 unverändert:
- B110 (try/except/pass): 3× — Bestandslogik, kein Security-Fix nötig
- B105 (Hardcoded-Token-Limits): 4× — Konfigurationswerte, keine Passwörter
- B104 (Bind 0.0.0.0): 2× — Lokale Entwicklungsumgebung
- B608 (SQL-Strings): 2× — False Positives (Logger-Ausgaben)
- B310 (urlopen): 1× — Submodul-Retriever, low priority
- B314 (XML-Parsing): 1× — PubMed-Retriever, Bestandslogik
- B301 (pickle): 1× — Cookie-Persistenz, Bestandslogik
- B403 (pickle-Import): 1× — Browser-Scraper, Bestandslogik
- B405 (XML-Import): 1× — PubMed-Retriever, Bestandslogik
- B112 (try/except/continue): 1× — Google-Retriever, Bestandslogik

---

## Upstream-/Fork-Empfehlung

Alle Änderungen sind upstream-kompatibel:
1. **MD5→`usedforsecurity=False`**: Upstream-PR-fähig. Keine Breaking Changes.
2. **Requests-Timeout**: Upstream-PR-fähig. Verbessert Robustheit ohne API-Bruch.
3. **SSL-Verify**: Akzeptiertes Fallback-Pattern. Keine Änderung nötig.

Empfohlen: Diese Änderungen als Upstream-PR an GPT Researcher vorschlagen.

---

## Folge-Issues

1. Submodul-Upstream-PR vorbereiten (MD5 + Timeout-Fixes)
2. Bandit-Baseline für verbleibende Vendor-Findings erstellen
3. Security-Regression-Tests für Netzwerk-Timeouts
