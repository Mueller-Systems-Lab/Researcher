# Researcher — Nächstes Issue: Optionaler Runtime-Smoke-Test für Ollama + SearXNG + Tor

## Rolle

Du bist ein Senior Runtime Reliability Engineer und Local-First Integration Tester.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-Chain:

- #50: Walking-Skeleton/Repair
- #51: ruff Lint-/CI-Gate, 950 → 0
- #52: Bandit-/Security-Triage
- #53: Submodul-Security-Review
- #54: CI-Security-Gate
- #55: mypy Vendor-/Submodul-Grenze
- #56: Projekt-Type-Errors 33 → 0, `make typecheck` blockierend
- #57: Testprofile getrennt
- #58: Fresh-Clone-Onboarding

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, die echte lokale Runtime-Pipeline optional und reproduzierbar zu prüfen:

- Ollama
- SearXNG
- Tor
- lokale Research-Pipeline
- keine externen Cloud-APIs
- keine Pflicht für normale CI

---

# Ausgangslage

Nach #58 sind die lokalen Quality-Gates stabil:

```bash
make quality    # ca. 30s, grün
make coverage   # ca. 10s, >=78%
make test-e2e   # ca. 2s, grün
make ci-local   # ca. 45s, grün
make ci-full    # ca. 5min, grün inkl. Benchmarks
```

Diese Gates beweisen Codequalität, Testbarkeit und Onboarding.

Sie beweisen aber noch nicht vollständig, dass die echte Runtime-Pipeline mit lokalen Diensten läuft.

---

# Oberstes Ziel dieses Issues

Erstelle einen optionalen Runtime-Smoke-Test, der beweist:

1. Ollama ist erreichbar.
2. Das konfigurierte lokale Modell ist vorhanden oder sauber als fehlend gemeldet.
3. SearXNG ist erreichbar.
4. Tor SOCKS5 ist erreichbar oder sauber als fehlend gemeldet.
5. Cloud-/Remote-Provider sind nicht aktiv.
6. Eine minimale Research-Anfrage kann in kontrolliertem Modus laufen.
7. Fehler werden klar klassifiziert.
8. Der Test ist optional und nicht Bestandteil des schnellen CI-Pfads.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- produktive Architektur umbauen
- externe Cloud-APIs aktivieren
- echte Darknet-Ziele automatisch crawlen
- lange oder riskante Live-Recherchen starten
- CI von Ollama/SearXNG/Tor abhängig machen
- Quality-Gates lockern
- Tests löschen
- Coverage-Schwelle senken
- Vendor-Code unnötig ändern

---

# Sicherheits- und Scope-Regeln

## Local-first

Der Runtime-Smoke-Test MUSS lokal bleiben.

Er darf keine OpenAI-, Tavily-, SerpAPI- oder sonstige Cloud-API verwenden, außer der Nutzer hat das explizit aktiviert.

## Keine riskante Live-Recherche

Der Smoke-Test darf höchstens eine harmlose, kurze Query verwenden.

Beispiele:

```text
local test query
example domain test
what is a search engine
```

Keine Security-Zielsuche, keine Exploit-Suche, keine personenbezogenen Queries.

## Tor optional

Tor ist optional.

Wenn Tor nicht läuft:

- klar melden
- Smoke-Test nicht hart fehlschlagen lassen, außer `REQUIRE_TOR=true` gesetzt ist

## SearXNG optional, aber für Web-Runtime relevant

SearXNG ist für echte lokale Websuche wichtig.

Wenn SearXNG nicht läuft:

- klar melden
- Startanweisung ausgeben
- optional als Warnung behandeln

---

# Arbeitsreihenfolge

## 1. Aktuelle Runtime-Doku prüfen

Lies:

```text
README.md
docs/development/fresh-clone-onboarding.md
docs/testing/test-profiles.md
.env.example
scripts/
searxng/docker-compose.yml
Makefile
```

Dokumentiere:

- wie Ollama gestartet werden soll
- welches Modell erwartet wird
- wie SearXNG gestartet wird
- wie Tor erwartet wird
- welche Ports genutzt werden
- welche Umgebungsvariablen relevant sind

---

## 2. Runtime-Healthcheck-Skript erstellen

Erstelle ein kleines Skript, z. B.:

```text
scripts/runtime_smoke.py
```

oder, falls Projektkonvention anders ist, passend integrieren.

Das Skript soll prüfen:

### Ollama

- `OLLAMA_BASE_URL`, Default `http://localhost:11434`
- `/api/tags` oder äquivalenter lokaler Healthcheck
- erwartetes Modell aus `.env`/Config
- klare Ausgabe:
  - erreichbar
  - nicht erreichbar
  - Modell fehlt
  - Timeout

### SearXNG

- `SEARXNG_URL`, Default `http://localhost:8080`
- `/search?q=test&format=json`
- Timeout verwenden
- klare Ausgabe:
  - erreichbar
  - nicht erreichbar
  - liefert keine Ergebnisse
  - falsches Format

### Tor

- `TOR_SOCKS_HOST`, Default `127.0.0.1`
- `TOR_SOCKS_PORT`, Default `9050`
- Socket-Verbindungstest
- optionaler HTTP-Test nur wenn bereits im Projekt vorgesehen
- klare Ausgabe:
  - erreichbar
  - nicht erreichbar
  - optional übersprungen

### Cloud-Blocker

Prüfe relevante Env-Werte:

- OpenAI
- Tavily
- SerpAPI
- andere Cloud-Provider

Wenn Cloud-Provider aktiv sind und `ALLOW_CLOUD` nicht explizit gesetzt ist:

- Fehler melden
- Exit non-zero

---

## 3. Makefile-Target ergänzen

Ergänze:

```makefile
runtime-smoke:
	python3 scripts/runtime_smoke.py
```

Optional:

```makefile
runtime-smoke-strict:
	REQUIRE_OLLAMA=true REQUIRE_SEARXNG=true REQUIRE_TOR=true python3 scripts/runtime_smoke.py
```

Regeln:

- `runtime-smoke` darf Warnungen für optionale Dienste ausgeben.
- `runtime-smoke-strict` darf hart fehlschlagen.
- Kein bestehendes Quality-Gate darf von diesen Diensten abhängig werden.

---

## 4. Tests ergänzen

Erstelle Unit-Tests für das Runtime-Smoke-Skript mit Mocks.

Ziele:

- Ollama erreichbar
- Ollama nicht erreichbar
- Modell fehlt
- SearXNG erreichbar
- SearXNG Timeout
- Tor Socket erreichbar/nicht erreichbar
- Cloud-Provider aktiv ohne `ALLOW_CLOUD`
- optionaler Dienst fehlt → Warnung statt harter Fehler
- strict mode → harter Fehler

Die Tests dürfen keine echten Netzwerkdienste benötigen.

---

## 5. Dokumentation erstellen

Erstelle oder aktualisiere:

```text
docs/runtime/local-runtime-smoke.md
```

Pflichtinhalt:

```markdown
# Local Runtime Smoke Test

## Ziel

## Was geprüft wird

| Dienst | Default | Pflicht im Standardmodus | Pflicht im Strict Mode |
|---|---|---|---|
| Ollama | localhost:11434 | Nein/Warnung | Ja |
| SearXNG | localhost:8080 | Nein/Warnung | Ja |
| Tor | 127.0.0.1:9050 | Nein/Warnung | Ja |

## Befehle

```bash
make runtime-smoke
make runtime-smoke-strict
```

## Erwartete Ausgabe

## Dienste starten

### Ollama

### SearXNG

### Tor

## Cloud-Blocker

## Troubleshooting

## CI-Hinweis
```

README optional verlinken:

```markdown
## Optional Runtime Smoke Test

```bash
make runtime-smoke
```
```

---

# Validierung

Nach Änderungen ausführen:

```bash
# bestehende Gates
make quality
make coverage
make test-e2e
make ci-local

# neue Runtime-Smoke-Tests
python3 -m pytest tests/ -q -k "runtime_smoke or runtime"

# Runtime Smoke Standard
make runtime-smoke

# Strict nur ausführen, wenn Dienste tatsächlich laufen
make runtime-smoke-strict
```

Falls Dienste nicht laufen:

- `make runtime-smoke` darf nicht hart fehlschlagen, sofern Standardmodus optional ist.
- `make runtime-smoke-strict` darf fehlschlagen und muss klar sagen, was fehlt.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Runtime-Smoke-Skript existiert
- Makefile-Target `runtime-smoke` existiert
- optionales Strict-Target existiert oder begründet weggelassen wurde
- Ollama-Healthcheck implementiert ist
- SearXNG-Healthcheck implementiert ist
- Tor-Healthcheck implementiert ist
- Cloud-Blocker geprüft wird
- Unit-Tests ohne echte Dienste existieren
- Standardmodus ist CI-sicher und optional
- Strict-Modus kann echte Runtime prüfen
- Dokumentation existiert
- README verlinkt Runtime-Smoke-Test
- bestehende Gates bleiben grün
- keine produktiven Features gebaut wurden
- GitHub-Kommentar mit Ergebnissen geschrieben wurde

Minimal akzeptabel:

- `make runtime-smoke` prüft Ollama/SearXNG/Tor/Cloud-Config und gibt klare Diagnose aus
- Tests mocken die wichtigsten Fälle
- Doku vorhanden
- keine Regression bei `make ci-local`

Gut:

- `runtime-smoke-strict` prüft echte Dienste hart
- Troubleshooting ist copy-paste-fähig
- `.env.example` enthält alle relevanten Runtime-Variablen

Sehr gut:

- ein Nutzer kann lokale Dienste starten und mit einem Befehl die echte Research-Runtime validieren
- Smoke-Test unterscheidet sauber Warnung, Fehler und Strict-Failure
- später leicht in manuelle CI/workflow_dispatch integrierbar

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Runtime-Smoke Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Runtime-Smoke-Skript erstellt | |
| `make runtime-smoke` vorhanden | |
| `make runtime-smoke-strict` vorhanden | |
| Ollama-Check implementiert | |
| SearXNG-Check implementiert | |
| Tor-Check implementiert | |
| Cloud-Blocker geprüft | |
| Unit-Tests ohne echte Dienste vorhanden | |
| Doku erstellt | |
| README aktualisiert | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Keine produktiven Features | |
| GitHub-Kommentar geschrieben | |

## Runtime-Ergebnisse

| Dienst | Ergebnis | Modus | Bemerkung |
|---|---|---|---|
| Ollama | | standard/strict | |
| SearXNG | | standard/strict | |
| Tor | | standard/strict | |
| Cloud-Blocker | | standard/strict | |

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

1. `Playwright-CI-Strategie definieren`
2. `Security regression tests für Netzwerk-/Hashing-/SQL-Pfade ergänzen`
3. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
4. `Minimaler echter Research-Happy-Path mit lokalen Diensten`
