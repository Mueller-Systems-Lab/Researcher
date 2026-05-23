# Researcher — Nächstes Issue: Security Regression Tests für Netzwerk-, Hashing- und SQL-Pfade ergänzen

## Rolle

Du bist ein Senior Python Security Test Engineer und Regression-Guard-Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Chain:

- #50: Walking-Skeleton
- #51: ruff 950 → 0
- #52: Bandit Triage
- #53: Submodul Security
- #54: CI Security Gate
- #55: mypy Boundary
- #56: Type Errors 33 → 0
- #57: Test Profiles
- #58: Fresh-Clone-Onboarding
- #59: Runtime Smoke
- #60: SearXNG Runtime
- #61: Minimal Research-Happy-Path
- #62: Ollama Config
- #63: Report Eval
- #64: Report Traceability
- #65: Source Coverage
- #66: Multi-Query Eval
- #67: Report Quality Regression Guard

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die bereits identifizierten und teilweise gehärteten Security-Risiken dauerhaft gegen Regressionen abzusichern.

---

# Ausgangslage

Nach #67 ist das Projekt in einem sehr guten Zustand:

```bash
make quality                         # grün, ca. 30s
make coverage                        # 78.5%, grün
make runtime-smoke                   # 4/4 Dienste
make research-happy-path             # Query → Report
make research-evaluate               # Single Report Evaluation
make research-evaluate-multi         # Multi Query Evaluation
python3 scripts/research_multi_query_eval.py --baseline docs/evaluation/report-quality-baseline.json --fail-on-regression
```

Bekannte Security-Historie:

- #52: 43 Bandit-Findings triagiert
- #53: Submodul-Security-Review
  - 6 MD5-Stellen mit `usedforsecurity=False`
  - 8 `requests`-Timeouts ergänzt
  - SSL-Verify-Fallback dokumentiert
- #54: Hybrid Security Gate
  - Projektcode blockierend ab Medium
  - Vendor/Submodul report-only
- Projektcode hat 0 Medium/High Bandit-Findings

Jetzt fehlt:

> Tests, die verhindern, dass Netzwerk-Timeouts, unsichere Hash-Nutzung, SQL-String-Building oder Cloud-Fallbacks unbemerkt zurückkommen.

---

# Oberstes Ziel dieses Issues

Ergänze fokussierte Security Regression Tests für:

1. Netzwerkaufrufe müssen Timeouts verwenden.
2. Cloud-Provider dürfen im Local-First-Modus nicht aktiv werden.
3. MD5 darf nicht sicherheitsrelevant verwendet werden.
4. SQL-Pfade müssen parametrisiert oder datenflussbasiert sicher sein.
5. SSL-Verify-Ausnahmen müssen eng begrenzt und dokumentiert bleiben.
6. Security-Policy und Tests müssen zusammenpassen.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Security-Features bauen
- produktive Architektur umbauen
- neue Provider integrieren
- Cloud-Fallbacks einführen
- Vendor-Code großflächig refactoren
- Bandit-Regeln lockern
- `# nosec` pauschal hinzufügen
- Quality Gates lockern
- Coverage-Schwelle senken
- Tests löschen
- riskante Live-Netzwerkaufrufe in Unit-Tests machen

---

# Security-Regressionsprinzipien

## 1. Tests vor Konfiguration

Wenn ein Risiko wichtig genug für Bandit-Triage war, sollte es mindestens einen Regressionstest geben.

## 2. Keine echten externen Dienste

Security Regression Tests müssen gemockt sein.

Keine echten Requests an:

- Internet
- SearXNG live
- Tor live
- Ollama live
- externe URLs

## 3. Projektcode zuerst

Priorität:

1. Projekt-eigene Module
2. Submodul-Hardening-Stellen aus #53, wenn stabil testbar
3. Doku/Policy-Konsistenz

## 4. Kein False-Security-Theater

Tests sollen echtes Verhalten prüfen, nicht nur Strings.

Beispiel gut:

- `requests.get` wird gemockt und Assertion prüft `timeout=(5, 30)`.

Beispiel schwach:

- nur grep nach `timeout`.

---

# Arbeitsreihenfolge

## 1. Security-Historie und betroffene Dateien lesen

Lies:

```text
docs/security/bandit-triage.md
docs/security/submodule-security-review.md
docs/security/security-gate-policy.md
Makefile
scripts/runtime_smoke.py
scripts/research_happy_path.py
scripts/research_multi_query_eval.py
gpt_researcher/
search/
crawlers/
darknet_search/
mcp_tools/
vectordb/
```

Dokumentiere:

- welche Netzwerkaufrufe produktiv sind
- welche Netzwerkaufrufe bereits Timeout haben
- wo Cloud-Provider blockiert werden
- wo Hashing verwendet wird
- wo SQL verwendet wird
- welche Bandit-Findings als akzeptiert dokumentiert sind

---

## 2. Netzwerk-Timeout Regression Tests

Erstelle oder erweitere:

```text
tests/test_security_regressions.py
```

oder sinnvoll aufteilen:

```text
tests/security/test_network_timeouts.py
tests/security/test_cloud_blocker.py
tests/security/test_hashing_regressions.py
tests/security/test_sql_regressions.py
```

Wenn neues Verzeichnis:

- `tests/security/__init__.py` hinzufügen, falls nötig.

Testfälle:

- `runtime_smoke` nutzt Timeouts bei Ollama/SearXNG-HTTP-Checks.
- `research_happy_path` nutzt Timeouts bei SearXNG/Ollama-Aufrufen.
- Submodul-Retriever aus #53 haben Timeouts, falls leicht importierbar/testbar.
- Kein produktiver `requests.get/post/request`-Call ohne Timeout in Projektpfaden.

Bevorzugt mit `unittest.mock`.

---

## 3. Cloud-Blocker Regression Tests

Testfälle:

- `OPENAI_API_KEY` gesetzt + `ALLOW_CLOUD` false → Abbruch.
- `TAVILY_API_KEY` gesetzt + `ALLOW_CLOUD` false → Abbruch.
- `ANTHROPIC_API_KEY` gesetzt + `ALLOW_CLOUD` false → Abbruch.
- `ALLOW_CLOUD=true` muss bewusst dokumentiert sein, aber nicht automatisch für Happy-Path genutzt werden.
- Report/Runtime-Smoke dokumentiert Cloud-Status `false`.

Wichtig:

- Environment sauber mit `monkeypatch` isolieren.
- Keine echten Keys verwenden.

---

## 4. Hashing Regression Tests

Ziel:

- Sicherheitsrelevante Hash-Nutzung darf nicht MD5 verwenden.
- bekannte nicht-sicherheitsrelevante MD5-Stellen müssen `usedforsecurity=False` verwenden oder dokumentiert sein.

Testmöglichkeiten:

- gezielte Unit-Tests für eigene Hash-Funktionen, falls vorhanden.
- statische, eng begrenzte Prüfung für `hashlib.md5(` im Projektcode:
  - erlaubt nur mit `usedforsecurity=False`
  - Vendor-Ausnahmen aus Policy berücksichtigen

Keine große neue Static-Analysis-Engine bauen.

---

## 5. SQL Regression Tests

Ziel:

- SQL-String-Building mit untrusted Input darf nicht zurückkommen.
- bekannte False Positives aus #52 bleiben dokumentiert.

Vorgehen:

- Suche nach `execute(f"` / `.format(` in SQL-Kontexten.
- Wenn projekt-eigene SQL-Funktionen existieren: Tests mit bösartigem Input, der als Parameter behandelt wird.
- Wenn keine direkte SQL-Schicht im Projektcode existiert: dokumentiere das und ergänze begrenzten statischen Regressionstest.

Beispieltest:

```python
def test_sql_queries_do_not_use_f_strings_for_user_input():
    ...
```

Nur auf Projektpfade anwenden, nicht blind auf Vendor.

---

## 6. SSL-Verify Regression

Für die bekannte SSL-Verify-Ausnahme:

- prüfen, dass sie in Policy dokumentiert ist
- prüfen, dass keine neue `verify=False`-Stelle im Projektcode auftaucht
- Vendor-Ausnahme separat behandeln

Test:

- statische begrenzte Suche nach `verify=False`
- erlaubte Pfade aus allowlist
- allowlist muss klein und dokumentiert sein

---

## 7. Makefile-Target ergänzen

Ergänze:

```makefile
security-regression:
	python3 -m pytest tests/ -q -k "security_regression or security"
```

Falls eigenes Verzeichnis:

```makefile
security-regression:
	python3 -m pytest tests/security/ -q
```

Optional in `quality` aufnehmen?

Empfehlung:

- Wenn Tests schnell und rein gemockt sind: in `make quality` aufnehmen.
- Wenn langsam oder statisch breit: eigenes Target und optional `ci-local`.

Bevorzugter Zielzustand:

```makefile
quality:
	python3 -m ruff check . --line-length=88
	$(MAKE) typecheck
	$(MAKE) security-project
	$(MAKE) security-regression
	$(MAKE) test-fast
```

Nur aufnehmen, wenn Laufzeit klein bleibt.

---

## 8. Dokumentation aktualisieren

Aktualisiere oder erstelle:

```text
docs/security/security-regression-tests.md
```

Pflichtinhalt:

```markdown
# Security Regression Tests

## Ziel

## Abgedeckte Risiken

| Risiko | Teststrategie |
|---|---|
| Requests ohne Timeout | Mock-Assertions |
| Cloud-Fallback | Env-Tests |
| MD5 | usedforsecurity=False / Allowlist |
| SQL-Injection | Parameterization/static guard |
| SSL verify=False | Allowlist/Policy check |

## Befehle

```bash
make security-regression
make quality
```

## Scope

## Allowlist

## Grenzen
```

Aktualisiere ggf.:

```text
docs/security/security-gate-policy.md
```

---

# Validierung

Nach Änderungen ausführen:

```bash
# neue Security Regression Tests
make security-regression

# bestehende Gates
make quality
make coverage
make test-e2e
make ci-local

# Security
make security-project
make security-vendor
make security-report

# Runtime/Eval optional
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make research-evaluate-regression
```

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Security Regression Tests existieren
- Netzwerk-Timeouts durch Tests abgesichert sind
- Cloud-Blocker durch Tests abgesichert ist
- MD5/Hashing-Regression abgesichert oder dokumentiert ist
- SQL-Regression abgesichert oder dokumentiert ist
- SSL-Verify-Ausnahmen durch Allowlist/Policy abgesichert sind
- `make security-regression` existiert
- Tests sind gemockt und ohne externe Dienste
- Doku existiert
- `make quality` bleibt grün
- `make coverage` bleibt grün
- `make ci-local` bleibt grün
- keine Cloud-Fallbacks eingeführt wurden
- keine neuen Features gebaut wurden
- GitHub-Kommentar mit Ergebnissen geschrieben wurde

Minimal akzeptabel:

- Cloud-Blocker + Timeout-Regression Tests
- `make security-regression`
- Doku
- keine Regression

Gut:

- Hashing, SQL und SSL-Verify ebenfalls abgesichert
- Tests laufen schnell genug für `make quality`

Sehr gut:

- `security-regression` wird Teil von `make quality`
- Security-Gate schützt nicht nur Bandit-Status, sondern konkrete Verhaltensregressionen

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Security Regression Tests Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Security Regression Tests erstellt | |
| Netzwerk-Timeouts abgesichert | |
| Cloud-Blocker abgesichert | |
| MD5/Hashing abgesichert | |
| SQL-Regressionsschutz vorhanden | |
| SSL-Verify-Allowlist/Policy geprüft | |
| `make security-regression` vorhanden | |
| Tests ohne externe Dienste | |
| Doku erstellt | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine Cloud-Fallbacks | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Neue Tests

| Bereich | Anzahl | Bemerkung |
|---|---:|---|
| Netzwerk-Timeouts | | |
| Cloud-Blocker | | |
| Hashing | | |
| SQL | | |
| SSL Verify | | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## Allowlist/akzeptierte Ausnahmen

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Playwright-CI-Strategie definieren`
2. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
3. `Research Evaluation Dataset: harmlose Query-Fixtures versionieren`
4. `Release Readiness: Version, Changelog, Known Limitations`
