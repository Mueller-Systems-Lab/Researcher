# Researcher — Nächstes Issue: Minimaler echter Research-Happy-Path mit lokalen Diensten

## Rolle

Du bist ein Senior Local-First Integration Engineer und Research-Pipeline Reliability Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-/Runtime-Chain:

- #50: Walking-Skeleton
- #51: ruff Lint 950 → 0
- #52: Bandit Triage
- #53: Submodul Security
- #54: CI Security Gate
- #55: mypy Boundary
- #56: Type Errors 33 → 0
- #57: Test Profiles
- #58: Fresh-Clone-Onboarding
- #59: Runtime Smoke
- #60: SearXNG Runtime stabilisiert

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, den kleinsten echten lokalen Research-Happy-Path kontrolliert auszuführen und abzusichern.

---

# Ausgangslage

Nach #60 ist der Runtime-Smoke grün:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
```

Ergebnis:

```text
Cloud:  ✅ Keine Cloud-Provider
Ollama: ✅ nomic-embed-text:latest
SearXNG: ✅ 11 results
Tor:    ✅ SOCKS5 127.0.0.1:9050
Ergebnis: 4/4 Dienste erreichbar ✅
```

Quality-Pipeline:

```bash
make quality    # grün, ca. 30s
make coverage   # grün, >=78%
make test-e2e   # grün
make ci-local   # grün
make ci-full    # grün inkl. Benchmarks
```

Jetzt soll bewiesen werden:

> Eine minimale, harmlose Research-Anfrage kann mit lokalen Diensten durchlaufen, ohne Cloud-Provider, ohne riskante Zielsuche und ohne große Feature-Implementierung.

---

# Oberstes Ziel dieses Issues

Erstelle einen optionalen, sicheren, minimalen Research-Happy-Path:

1. prüft Runtime-Dienste vorher
2. führt eine harmlose Mini-Research-Query aus
3. nutzt lokale Komponenten
4. blockiert Cloud-Fallbacks
5. erzeugt einen kleinen Report oder strukturiertes Ergebnis
6. speichert keine sensiblen Daten
7. ist als optionales Makefile-Target ausführbar
8. hat gemockte Tests und optional einen Live-Smoke

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Research-Features bauen
- Exploit-, Security-Target-, Personen- oder Darknet-Recherche ausführen
- Cloud-APIs aktivieren
- externe API-Provider als Fallback nutzen
- lange Crawls starten
- automatisiert Darknet-Foren durchsuchen
- Produktivarchitektur umbauen
- Quality-Gates lockern
- Tests löschen
- Coverage-Schwelle senken
- Vendor-Code unnötig ändern

---

# Sicherheits- und Scope-Regeln

## Harmlose Query

Erlaubte Testqueries:

```text
What is SearXNG?
What is local search?
What is a search engine?
```

Nicht erlaubt:

```text
Exploit ...
CVE ...
site:target.com ...
person name ...
Darknet forum ...
credentials ...
```

## Lokale Dienste

Der Happy-Path darf nur lokale konfigurierte Dienste nutzen:

- Ollama
- SearXNG
- optional Tor, aber kein echter Darknet-Crawl
- lokale Dateipfade/temporäre Reports

## Cloud-Blocker

Vor Ausführung muss geprüft werden:

- keine Cloud-Provider aktiv
- `ALLOW_CLOUD` nicht gesetzt oder false
- keine OpenAI/Tavily/SerpAPI Keys im aktiven Pfad verwendet

Wenn Cloud aktiv ist:

- abbrechen
- klare Meldung ausgeben

---

# Arbeitsreihenfolge

## 1. Aktuelle Research-Entry-Points analysieren

Lies:

```text
README.md
scripts/
gpt_researcher/
search/
mcp_tools/
config/
.env.example
docs/runtime/local-runtime-smoke.md
docs/runtime/searxng-local-runtime.md
Makefile
```

Ermittle:

- Wie die Research-Pipeline aktuell gestartet wird
- Ob es einen CLI-Entry-Point gibt
- Wie SearXNG in die Pipeline eingebunden ist
- Welche LLM-/Embedding-Komponenten gebraucht werden
- Wo Reports ausgegeben werden
- Welche Env-Variablen den Cloud-Blocker steuern

Dokumentiere den kleinsten realistischen Pfad.

---

## 2. Happy-Path-Skript oder Target erstellen

Bevorzugt: kleines Skript, z. B.

```text
scripts/research_happy_path.py
```

oder bestehendes Skript erweitern, falls sinnvoll.

Das Skript soll:

1. `runtime_smoke`-Logik oder Checks wiederverwenden
2. Cloud-Blocker prüfen
3. SearXNG mit harmloser Query testen
4. Ollama minimal prüfen
5. optional eine sehr kurze lokale Report-Generierung anstoßen
6. Ergebnis in `reports/runtime/research-happy-path.md` oder `.json` schreiben
7. klaren Exit-Code liefern

Wenn die vollständige GPT-Researcher-Pipeline zu schwer ist:

- erst einen minimalen Integration-Pfad bauen:
  - Query → SearXNG results → kurzer lokaler LLM-Summary-Call → Report-Datei
- dokumentieren, dass dies ein Runtime-Happy-Path ist, kein vollständiger Produktiv-Research-Lauf

---

# 3. Makefile-Targets ergänzen

Ergänze:

```makefile
research-happy-path:
	SEARXNG_TIMEOUT_SECONDS=30 python3 scripts/research_happy_path.py

research-happy-path-strict:
	REQUIRE_OLLAMA=true REQUIRE_SEARXNG=true REQUIRE_TOR=false SEARXNG_TIMEOUT_SECONDS=30 python3 scripts/research_happy_path.py --strict
```

Optional:

```makefile
research-happy-path-clean:
	rm -rf reports/runtime/research-happy-path.*
```

Regeln:

- Target ist optional.
- Nicht Bestandteil von `make quality`.
- Nicht Bestandteil von `make ci-local`.
- Darf Teil von `make ci-full` nur dann werden, wenn es ohne echte externe Dienste zuverlässig ist. Sonst nicht.

---

## 4. Tests ergänzen

Gemockte Tests für:

- Cloud aktiv → Abbruch
- SearXNG liefert Ergebnisse → Report wird erzeugt
- SearXNG Timeout → klare Fehlermeldung
- Ollama nicht erreichbar → klare Fehlermeldung
- Query-Safety-Guard blockiert riskante Query
- Report-Pfad wird erzeugt
- Strict Mode schlägt bei fehlendem Dienst fehl

Keine echten Netzwerkaufrufe in Unit-Tests.

---

## 5. Query-Safety-Guard einbauen

Vor Ausführung prüfen:

Riskante Begriffe/Pattern blockieren:

```text
exploit
cve
vulnerability
target.com
credentials
password dump
darknet
onion forum
person:
site:
```

Diese Liste muss nicht perfekt sein. Sie dient nur dazu, den Smoke-Test harmlos zu halten.

Bei blockierter Query:

- Exit non-zero
- Meldung: „Smoke-Test erlaubt nur harmlose generische Queries.“

---

## 6. Dokumentation erstellen

Erstelle:

```text
docs/runtime/research-happy-path.md
```

Pflichtinhalt:

```markdown
# Minimal Local Research Happy Path

## Ziel

## Was dieser Test beweist

## Was dieser Test nicht beweist

## Voraussetzungen

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
```

## Ausführen

```bash
make research-happy-path
```

## Strict Mode

```bash
make research-happy-path-strict
```

## Erwartete Ausgabe

## Report-Pfad

## Sicherheitsgrenzen

## Troubleshooting

## Nächste Schritte
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

# Runtime
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke

# neue Tests
python3 -m pytest tests/ -q -k "research_happy_path or runtime_smoke"

# optional live
make research-happy-path
```

Falls lokale Dienste verfügbar sind:

```bash
make research-happy-path-strict
```

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- minimaler Research-Happy-Path als optionales Target existiert
- Cloud-Blocker vor Ausführung greift
- harmlose Query verwendet wird
- Query-Safety-Guard existiert
- SearXNG wird real oder gemockt eingebunden
- Ollama wird real oder gemockt eingebunden
- Report-/Ergebnisdatei wird erzeugt
- Unit-Tests ohne echte Dienste existieren
- Doku existiert
- README verlinkt optional
- bestehende Gates bleiben grün
- keine riskante Recherche durchgeführt wurde
- keine neuen Produktfeatures gebaut wurden
- GitHub-Kommentar mit Ergebnis geschrieben wurde

Minimal akzeptabel:

- Query → SearXNG → lokaler Ergebnisreport
- Cloud-Blocker
- Tests
- Doku
- keine Regression

Gut:

- Query → SearXNG → Ollama Summary → Markdown Report
- Strict Mode funktioniert lokal
- Runtime-Smoke wird vorher verwendet

Sehr gut:

- Der Nutzer kann mit zwei Befehlen die lokale Runtime und einen Mini-Research-Report validieren:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
make research-happy-path
```

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Minimal Research-Happy-Path Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Optionales Target erstellt | |
| Strict Target erstellt | |
| Cloud-Blocker integriert | |
| Query-Safety-Guard integriert | |
| SearXNG eingebunden | |
| Ollama eingebunden | |
| Report-Datei erzeugt | |
| Unit-Tests vorhanden | |
| Doku erstellt | |
| README aktualisiert | |
| `make quality` weiterhin grün | |
| `make coverage` weiterhin grün | |
| `make ci-local` weiterhin grün | |
| Runtime-Smoke weiterhin grün | |
| Keine riskante Recherche | |
| Keine neuen Features | |
| GitHub-Kommentar geschrieben | |

## Live-Ergebnis

| Schritt | Ergebnis |
|---|---|
| runtime-smoke | |
| research-happy-path | |
| Report-Pfad | |

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
4. `Research Report Quality Evaluation: Quellen, Halluzinationen, Evidenz`
