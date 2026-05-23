# Researcher — Nächstes Issue: SearXNG Runtime stabilisieren und lokalen Search-Smoke absichern

## Rolle

Du bist ein Senior Local-First Runtime Engineer und Search Integration Debugging Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-Chain:

- #50: Walking-Skeleton/Repair
- #51: ruff Lint-Gate
- #52: Bandit-Triage
- #53: Submodul-Security-Review
- #54: CI-Security-Gate
- #55: mypy Vendor-Grenze
- #56: Projekt-Type-Errors 33 → 0
- #57: Testprofile
- #58: Fresh-Clone-Onboarding
- #59: Runtime-Smoke für Ollama + SearXNG + Tor + Cloud-Blocker

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, den in #59 sichtbaren SearXNG-Timeout zu analysieren und den lokalen Search-Smoke so zu stabilisieren, dass ein späterer echter Research-Happy-Path auf einer belastbaren Suchruntime aufsetzt.

---

# Ausgangslage

Nach #59 ist die Quality Pipeline stabil:

```bash
make quality       # grün, ~30s
make coverage      # grün, >=78%
make test-e2e      # grün
make ci-local      # grün
make ci-full       # grün
make runtime-smoke # optional
```

Runtime-Smoke lokal:

| Dienst | Ergebnis | Bemerkung |
|---|---|---|
| Ollama | ✅ | erreichbar, Modell vorhanden |
| Tor | ✅ | SOCKS5 erreichbar |
| Cloud-Blocker | ✅ | keine Cloud aktiv |
| SearXNG | ⚠️ | Timeout, optional |

Der SearXNG-Timeout ist kein Quality-Gate-Fehler, aber ein Risiko für den nächsten echten Research-Happy-Path.

---

# Oberstes Ziel dieses Issues

Stabilisiere die lokale SearXNG-Integration so, dass:

1. SearXNG zuverlässig startbar ist.
2. der Healthcheck zwischen „nicht gestartet“, „gestartet aber nicht bereit“, „Timeout“, „falsches Format“ und „ok“ unterscheidet.
3. `make runtime-smoke` SearXNG sauber diagnostiziert.
4. optional `make searxng-up`, `make searxng-down`, `make searxng-logs`, `make searxng-smoke` existieren.
5. ein späterer minimaler echter Research-Happy-Path nicht an unklarer Search-Runtime scheitert.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- produktive Research-Logik ändern
- externe Cloud-Suchprovider aktivieren
- Darknet-Crawling starten
- CI von SearXNG abhängig machen
- Quality Gates lockern
- Coverage senken
- Tests löschen
- Ollama- oder Tor-Integration umbauen
- Vendor-Code unnötig anfassen

---

# Sicherheits- und Scope-Regeln

## Keine Cloud-Fallbacks

Wenn SearXNG nicht läuft, darf nicht automatisch auf Google, Bing, Tavily, SerpAPI oder andere Cloud-/Remote-Provider gewechselt werden.

## Lokale Diagnose statt Featurebau

Der Fokus liegt auf Startbarkeit, Healthcheck, Timeouts und Dokumentation.

## Keine echte riskante Suche

Smoke-Queries müssen harmlos sein:

```text
test
example
local search test
```

Keine Exploit-, Ziel-, Personen- oder Darknet-Queries.

---

# Arbeitsreihenfolge

## 1. Aktuelle SearXNG-Konfiguration analysieren

Lies:

```text
searxng/docker-compose.yml
searxng/
.env.example
README.md
docs/runtime/local-runtime-smoke.md
scripts/runtime_smoke.py
Makefile
search/
```

Dokumentiere:

- erwarteter Port
- erwartete URL
- Docker-Service-Name
- Healthcheck, falls vorhanden
- Timeout im Runtime-Smoke
- Format der Search-URL
- ob SearXNG JSON-Antworten erlaubt
- ob lokale Rate-Limits oder Bot-Schutz greifen

---

## 2. Lokalen Zustand reproduzieren

Führe aus:

```bash
make runtime-smoke
docker compose -f searxng/docker-compose.yml ps || true
docker compose -f searxng/docker-compose.yml logs --tail=100 || true
curl -v "http://localhost:8080/search?q=test&format=json" --max-time 10 || true
```

Falls Docker Compose nicht verfügbar ist, dokumentiere das sauber.

---

## 3. Makefile-Targets ergänzen

Falls noch nicht vorhanden, ergänze minimal:

```makefile
searxng-up:
	docker compose -f searxng/docker-compose.yml up -d

searxng-down:
	docker compose -f searxng/docker-compose.yml down

searxng-logs:
	docker compose -f searxng/docker-compose.yml logs --tail=100

searxng-smoke:
	python3 scripts/runtime_smoke.py --only searxng
```

Wenn `scripts/runtime_smoke.py` noch kein `--only` unterstützt, entweder:

- minimal implementieren, oder
- `searxng-smoke` als kleinen curl-/Python-Check umsetzen.

Keine großen CLI-Frameworks einführen.

---

## 4. Runtime-Smoke verbessern

`scripts/runtime_smoke.py` soll bei SearXNG unterscheiden:

- `OK`
- `NOT_RUNNING`
- `TIMEOUT`
- `BAD_STATUS`
- `BAD_JSON`
- `NO_RESULTS`
- `CONFIG_ERROR`

Empfehlung:

- Timeout konfigurierbar machen, z. B. `SEARXNG_TIMEOUT_SECONDS`, Default 10.
- URL aus `SEARXNG_URL` lesen, Default `http://localhost:8080`.
- Query harmlos halten.
- Fehlerausgabe copy-paste-fähig machen.

Beispielausgabe:

```text
SearXNG: TIMEOUT
URL: http://localhost:8080/search?q=test&format=json
Hint:
  make searxng-up
  make searxng-logs
  curl "http://localhost:8080/search?q=test&format=json" --max-time 10
```

---

## 5. Tests ergänzen

Ergänze gemockte Tests für SearXNG:

- OK mit JSON
- Timeout
- Connection refused
- HTTP 500
- Invalid JSON
- JSON ohne Ergebnisse
- Custom `SEARXNG_URL`
- Custom Timeout

Keine echten Docker-/Netzwerkdienste in Unit-Tests verwenden.

---

## 6. Dokumentation aktualisieren

Aktualisiere:

```text
docs/runtime/local-runtime-smoke.md
```

Ergänze oder erstelle:

```text
docs/runtime/searxng-local-runtime.md
```

Pflichtinhalt:

```markdown
# SearXNG Local Runtime

## Ziel

## Starten

```bash
make searxng-up
```

## Prüfen

```bash
make searxng-smoke
make runtime-smoke
curl "http://localhost:8080/search?q=test&format=json" --max-time 10
```

## Logs

```bash
make searxng-logs
```

## Stoppen

```bash
make searxng-down
```

## Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| Timeout | Container startet langsam / Netzwerk | Logs prüfen, Timeout erhöhen |
| 403/429 | SearXNG-Limiter/Engine | Settings prüfen |
| BAD_JSON | Format nicht aktiviert | format=json prüfen |
| Connection refused | Container nicht gestartet | make searxng-up |
```

README optional verlinken.

---

# Validierung

Nach Änderungen ausführen:

```bash
# bestehende Gates
make quality
make coverage
make test-e2e
make ci-local

# SearXNG-spezifisch
make searxng-up
make searxng-smoke
make runtime-smoke
make searxng-logs
make searxng-down

# Tests für Runtime-Smoke
python3 -m pytest tests/ -q -k "runtime_smoke or searxng"
```

Wenn Docker/SearXNG lokal nicht verfügbar ist:

- Unit-Tests müssen trotzdem grün sein.
- Doku muss erklären, wie der Nutzer SearXNG startet.
- `runtime-smoke` darf SearXNG im Standardmodus als Warnung melden.
- `runtime-smoke-strict` darf hart fehlschlagen.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- SearXNG-Timeout aus #59 reproduziert oder sauber als Umgebungseffekt erklärt wurde
- SearXNG-Healthcheck bessere Fehlerklassen ausgibt
- `make searxng-up` existiert oder begründet nicht nötig ist
- `make searxng-smoke` existiert
- `make runtime-smoke` SearXNG klar diagnostiziert
- Tests für SearXNG-Smoke-Fälle existieren
- SearXNG-Doku existiert
- README oder Runtime-Doku verlinkt ist
- `make quality` weiterhin grün bleibt
- `make coverage` weiterhin >=78% bleibt
- `make ci-local` weiterhin grün bleibt
- keine produktiven Research-Features gebaut wurden
- GitHub-Kommentar mit SearXNG-Befund geschrieben wurde

Minimal akzeptabel:

- Timeout-Diagnose verbessert
- SearXNG-Doku vorhanden
- Tests für Timeout/OK/ConnectionError
- keine Regression bei Quality Gates

Gut:

- Makefile-Targets für up/down/logs/smoke
- `make searxng-smoke` funktioniert lokal
- klare Troubleshooting-Hinweise

Sehr gut:

- SearXNG läuft lokal stabil
- `make runtime-smoke` zeigt Ollama ✅, SearXNG ✅, Tor ✅, Cloud ✅
- nächster echter Research-Happy-Path kann ohne Infrastrukturunklarheit beginnen

---

# Abschlussbericht-Vorlage

```markdown
# Researcher SearXNG Runtime Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| SearXNG-Timeout analysiert | |
| Healthcheck verbessert | |
| `make searxng-up` vorhanden | |
| `make searxng-down` vorhanden | |
| `make searxng-logs` vorhanden | |
| `make searxng-smoke` vorhanden | |
| SearXNG-Tests ergänzt | |
| SearXNG-Doku erstellt | |
| Runtime-Doku aktualisiert | |
| `make runtime-smoke` verbessert | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine produktiven Features | |
| GitHub-Kommentar geschrieben | |

## Runtime-Ergebnisse

| Befehl | Ergebnis | Bemerkung |
|---|---|---|
| make searxng-up | | |
| make searxng-smoke | | |
| make runtime-smoke | | |
| curl ...format=json | | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Geänderte Dateien

## Bewusst nicht gelöste Probleme

## Risiken

## Nächstes empfohlenes Issue
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Minimaler echter Research-Happy-Path mit lokalen Diensten`
2. `Playwright-CI-Strategie definieren`
3. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
4. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
