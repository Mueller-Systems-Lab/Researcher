# Trigger-Prompt: Phase 9 Complete → Next Steps

Du bist der Issue Orchestrator. Befolge strikt das github-source-of-truth- und spec-driven-development-Mandat.

## Kontext-Shortcut (Stand 2026-06-05 09:40 UTC)

- **Repo:** xxammaxx/Researcher, **Branch:** main, **HEAD:** fbd588f (v0.3.0)
- **Phase 9 Status:** ✅ **COMPLETE** — Issues #147–#150 alle geschlossen
- **Uncommitted Changes:** 9 modified files + 1 new test file (siehe unten)
- **Working Tree:** dirty — alle Phase-9-Änderungen liegen uncommitted vor

### Phase 9 Abschluss-Metriken
- **1252 Tests** passed, **37 Security Tests** passed, **0 flaky**
- `make security-project`: **0 Medium/High**
- `make lint`: **0 Errors** (scripts/ + dashboard/)
- CHANGELOG.md: Phase 9 Eintrag vorhanden

### Uncommitted Phase 9 Changes

```
 M CHANGELOG.md                                   (+27 Phase 9 entry)
 M dashboard/server.py                            (+2 static-fallback route)
 M docs/development/phase8-acceptance-report.md   (+14 Known Issues monitoring table)
 M docs/security/bandit-triage.md                 (+66 updated triage)
 M scrapers/http_session.py                       (+10 timeout hardening)
 M scripts/ci_acceptance.py                       (+201 API v3.5.0 migration)
 M scripts/runtime_smoke.py                       (+79 engine count + dashboard check)
 M scripts/visual_e2e_acceptance.py               (+4 nosec annotations)
?? tests/security/test_network_timeout_regression.py  (NEW — 161 lines, 1 test)
```

---

## Schritt 1: Commit, Push & Tag v0.4.0 (Issue #150 Follow-through)

### Problem
Phase 9 Code liegt uncommitted. Release v0.4.0 muss getaggt und gepusht werden.

### Aktion
1. `git add` aller Phase-9-Dateien (9 modified + 1 new)
2. Commit mit Message: `"Phase 9: Operational Readiness — Pipeline Fix, Security, Runtime Monitoring (#147-#150)"`
3. `git tag -a v0.4.0 -m "Phase 9: Operational Readiness"`
4. `git push origin main --tags`
5. GitHub Release für v0.4.0 erstellen (mit CHANGELOG-Auszug)

### Acceptance Criteria
- [x] Alle Dateien committed
- [x] Tag v0.4.0 auf GitHub
- [x] GitHub Release mit Phase 9 Summary
- [x] `git status` clean

---

## Schritt 2: Live Acceptance Test (Issue #147 Validation)

### Problem
Die Pipeline-Fix-Änderungen wurden statisch validiert (Lint, Syntax, Unit-Tests), aber ein **End-to-End Live-Test mit laufenden Services** steht noch aus. Stage 2 ruft jetzt `POST /api/multi_agents` auf — dies muss gegen den echten GPT Researcher Docker-Container getestet werden.

### Voraussetzungen
```bash
# Alle 5 Services müssen laufen:
./start_all_services.sh --status
# Oder manuell:
# - Ollama (11434)
# - llama-server (8082)
# - SearXNG Docker (8090)
# - GPT Researcher Docker (28202)
# - Dashboard (8888)
```

### Aktion
1. `make acceptance` ausführen
2. Prüfen, dass **Stage 2 NICHT mehr** `⚠️ Skipped` zeigt
3. Prüfen, dass Stage 2 HTTP 200 von `/api/multi_agents` bekommt
4. Prüfen, dass ein Report in `gpt_researcher/outputs/` generiert wird
5. Prüfen, dass **alle 5 Gates grün** sind

### Acceptance Criteria
- [ ] `make acceptance`: Stage 2 zeigt HTTP 200
- [ ] `make acceptance`: Stage 2 zeigt kein `⚠️ Skipped`
- [ ] Report-Datei existiert in `gpt_researcher/outputs/`
- [ ] Alle 5 Gates: ✅

### Fehlerbehandlung
Falls Stage 2 fehlschlägt:
1. `docker logs` des GPT Researcher Containers prüfen
2. API direkt testen: `curl -X POST http://127.0.0.1:28202/api/multi_agents -H 'Content-Type: application/json' -d '{"query":"test","report_type":"research_report"}'`
3. Ggf. Payload-Format anpassen (die GPT Researcher v3.5.0 API kann je nach Build variieren)

---

## Schritt 3: Pre-Existing Test-Failures fixen (Issue #151)

### Problem
2 Tests scheitern bereits auf **clean main** (fbd588f) — nicht durch Phase 9 verursacht:

| Test | Fehler | Ursache |
|------|--------|---------|
| `test_composite_retriever_init` | Assertion `searx_url == "http://localhost:8080"` | `SEARX_URL` Env-Var überschreibt Default |
| `test_ollama_available` | `check_ollama()` erwartet Chat-Modell `qwen3.5:9b` | Config erwartet anderes Modell als Mock liefert |

### Aktion
1. **Issue #151 erstellen:** „Pre-Existing Test-Failures: composite + ollama smoke“
2. `test_composite_retriever_init`: Test auf Env-Var-Resilienz umbauen (nicht hart auf Port 8080 asserten)
3. `test_ollama_available`: Mock an aktuelles Chat-Modell anpassen (oder Config auslesen statt hart codieren)
4. Verifizieren: `pytest tests/test_composite.py::test_composite_retriever_init tests/test_runtime_smoke.py::test_ollama_available -v`
5. `make test-fast` — sicherstellen, dass 0 Failures übrig bleiben

### Acceptance Criteria
- [ ] `test_composite_retriever_init` passed
- [ ] `test_ollama_available` passed
- [ ] `make test-fast`: 0 Failures

---

## Schritt 4: Phase 10 Planung (Issue #152)

### Problem
Phase 9 hat die Infrastruktur gehärtet. Die eigentliche **Research-Qualität** wurde noch nicht systematisch evaluiert. Was kommt nach Operational Readiness?

### Mögliche Phase-10-Themen (zur Diskussion)
1. **Research Quality Benchmarking**: Multi-Query-Evaluation mit deutschen Queries, Halluzinationsrate messen
2. **Darknet-Search-Integration**: Tor-Crawling in Research-Pipeline einbinden (bisher nur isoliert)
3. **Submodul-Upstream-PRs**: Die 8 `requests`-ohne-Timeout-Findings als Upstream-PR an GPT Researcher senden
4. **MCP-Tool-Erweiterung**: Researcher-MCP um neue Tools ergänzen (Evidence-Retrieval, Audit-Export)
5. **Dashboard Live-Überwachung**: SSE-Stream stabilisieren, Prometheus-Metriken exportieren

### Aktion
1. **Issue #152 erstellen:** „Phase 10: Research Quality & Integration — Planning“
2. Die oben genannten Themen als Diskussionsgrundlage auflisten
3. Priorisierung basierend auf: Was bringt den höchsten Nutzerwert? Was ist am meisten blockiert?
4. `docs/development/phase10-planning.md` als Planning-Dokument anlegen

### Acceptance Criteria
- [ ] Issue #152 mit Phase-10-Themen erstellt
- [ ] Erste Priorisierung dokumentiert

---

## Schritt 5: Abschluss-Checkliste

- [ ] `git push origin main --tags` — Code + Tag live
- [ ] `make acceptance` grün (mit Stage 2 aktiv)
- [ ] `make quality` grün (0 lint, 0 type errors, 0 security Medium/High)
- [ ] `make runtime-smoke` erweitert (SearXNG Engines + Dashboard Fallback)
- [ ] 0 Test-Failures (nach Fix von #151)
- [ ] GitHub Release v0.4.0 published

---

## Zusammenfassung der nächsten Issues

| Issue | Titel | Priorität | Status |
|-------|-------|:---:|:---:|
| #150 | Commit + Tag v0.4.0 | 🔴 Hoch | Code liegt bereit |
| — | Live Acceptance Test | 🔴 Hoch | Benötigt Docker-Services |
| #151 | Pre-Existing Test-Failures fixen | 🟡 Mittel | 2 Failures |
| #152 | Phase 10 Planning | 🟢 Niedrig | Planung |

---

## Delegationsvorschlag

| Aufgabe | Agent | Grund |
|---------|-------|-------|
| Commit + Tag + Release | Orchestrator (selbst) | Git-Operationen |
| Live Acceptance Test | Orchestrator → Manuell triggern | Benötigt laufende Infrastruktur |
| #151 (Test-Fixes) | review-agent → Analyse + Fix | Code-Qualität |
| #152 (Planning) | architecture-agent → ADR/Planung | Architektur-Entscheidung |
