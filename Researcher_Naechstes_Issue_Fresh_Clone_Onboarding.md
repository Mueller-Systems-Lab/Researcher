# Researcher — Nächstes Issue: Developer Onboarding absichern (`fresh clone → green gates`)

## Rolle

Du bist ein Senior Developer Experience Engineer, Release-Readiness-Prüfer und CI-Reproduzierbarkeits-Agent.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Repair-Chain:

- #50: Walking-Skeleton/Repair
- #51: ruff Lint-/CI-Gate, 950 → 0
- #52: Bandit-/Security-Triage
- #53: Submodul-Security-Review
- #54: CI-Security-Gate
- #55: mypy Vendor-/Submodul-Grenze
- #56: Projekt-Type-Errors 33 → 0, `make typecheck` blockierend
- #57: Testprofile getrennt, `ci-local` ca. 45s, `ci-full` ca. 5min

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, nachzuweisen und zu dokumentieren, dass ein frischer Clone des Projekts reproduzierbar zu grünen Gates führt.

---

# Ausgangslage

Nach #57 existieren stabile Profile:

- `make test-fast` — 195 passed, ca. 15s
- `make test-e2e` — 9 passed, <1s
- `make test-benchmarks` — 9 passed, ca. 3min
- `make quality` — lint + typecheck + security + tests, ca. 30s
- `make coverage` — 78.52%, ca. 10s
- `make ci-local` — quality + coverage + e2e, ca. 45s
- `make ci-full` — alles inkl. benchmarks, ca. 5min

Alle Kern-Gates sind grün:

- ruff: 0 Errors
- typecheck: 0 Projekt-Type-Errors
- security-project: 0 Medium/High im Projektcode
- test-fast: 195 passed
- coverage: >=78%

Jetzt fehlt der harte Beweis:

> Kann ein neuer Entwickler oder eine frische Maschine das Projekt anhand der Dokumentation klonen, installieren und die grünen Gates reproduzieren?

---

# Oberstes Ziel dieses Issues

Erstelle und verifiziere einen Fresh-Clone-Onboarding-Pfad:

1. frischer Clone
2. Python-Version prüfen
3. virtuelle Umgebung erstellen
4. Dependencies installieren
5. notwendige optionale Dienste erklären
6. `make quality` grün
7. `make coverage` grün
8. `make test-e2e` grün
9. optional `make ci-local` grün
10. README/Developer-Doku so aktualisieren, dass der Pfad copy-paste-fähig ist

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik ändern
- Tests löschen
- Quality Gates lockern
- Coverage-Schwelle senken
- Security-Gate abschwächen
- Vendor-Code anfassen
- Playwright-CI vollständig lösen, falls dafür neue Runner-/Browser-Strategien nötig sind
- Ollama/SearXNG/Tor als Pflicht für den lokalen Quality-Loop erzwingen

---

# Onboarding-Prinzipien

## 1. Fresh Clone ist Wahrheit

Ein funktionierendes Projekt ist erst wirklich stabil, wenn es in einem neuen Verzeichnis reproduzierbar startet und die Gates laufen.

## 2. Lokaler Quality-Loop ohne externe Dienste

`make quality`, `make coverage` und `make test-e2e` müssen ohne Ollama, SearXNG und Tor laufen, sofern die Tests gemockt sind.

Externe Dienste gehören in separate optionale Abschnitte:

- Ollama
- SearXNG
- Tor
- GPU/NVIDIA
- Playwright visuell/accessibility
- Benchmarks

## 3. Copy-paste-fähige Befehle

README/Docs sollen konkrete Befehle enthalten, keine vagen Hinweise.

## 4. Troubleshooting ist Teil des Produkts

Typische Fehler sollen dokumentiert werden:

- falsche Python-Version
- fehlende venv
- fehlendes `bandit`
- fehlende Playwright-Browser
- Docker nicht verfügbar
- Ollama nicht gestartet
- SearXNG nicht gestartet
- NVIDIA/GPU nicht vorhanden

---

# Arbeitsreihenfolge

## 1. Fresh-Clone-Test vorbereiten

Erstelle außerhalb des aktuellen Repos einen frischen Testordner.

Beispiel:

```bash
mkdir -p /tmp/researcher-fresh-clone-test
cd /tmp/researcher-fresh-clone-test
git clone <REPO_URL> Researcher-fresh
cd Researcher-fresh
```

Dokumentiere:

- Repo-URL
- Branch
- Commit
- Betriebssystem
- Python-Version
- pip-Version
- ob Docker verfügbar ist
- ob NVIDIA/GPU verfügbar ist

Falls kein Netzwerk/Clone möglich ist, simuliere mit lokalem Clean-Checkout:

```bash
git status --short
git rev-parse HEAD
git clean -xfd -n
```

Aber bevorzugt ist ein echter Fresh Clone.

---

## 2. Installation reproduzieren

Führe aus:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Falls es ein Submodul gibt:

```bash
git submodule update --init --recursive
```

Prüfe, ob dieser Schritt in README fehlt.

Falls Dependencies nur mit Submodul korrekt funktionieren, dokumentiere das explizit.

---

## 3. Gates ausführen

Im frischen Clone ausführen:

```bash
make quality
make coverage
make test-e2e
make ci-local
```

Optional:

```bash
make test-benchmarks
make ci-full
make security-report
```

Dokumentiere:

- Laufzeit
- Ergebnis
- Fehler
- nötige manuelle Schritte
- ob `.env` nötig war
- ob externe Dienste nötig waren

---

## 4. README aktualisieren

Aktualisiere `README.md` oder passende Developer-Doku mit einem klaren Quickstart.

Pflichtabschnitt:

```markdown
## Fresh Clone Quickstart

```bash
git clone <REPO_URL>
cd Researcher
git submodule update --init --recursive

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

make quality
make coverage
make test-e2e
make ci-local
```

Expected result:

- `make quality`: lint/typecheck/security/test-fast green
- `make coverage`: >=78%
- `make test-e2e`: green
- `make ci-local`: green
```

Optionaler Abschnitt:

```markdown
## Optional Runtime Services

These are not required for the local quality loop:

- Ollama
- SearXNG
- Tor
- NVIDIA GPU dashboard
- Playwright visual/accessibility tests
```

---

## 5. Developer-Doku erstellen oder aktualisieren

Erstelle oder aktualisiere:

```text
docs/development/fresh-clone-onboarding.md
```

Pflichtinhalt:

```markdown
# Fresh Clone Onboarding

## Ziel

## Getestete Umgebung

| Feld | Wert |
|---|---|
| OS | |
| Python | |
| pip | |
| Branch | |
| Commit | |

## Schritte

## Quality Gates

| Befehl | Erwartung | Ergebnis |
|---|---|---|

## Optionale Dienste

## Troubleshooting

## Bekannte Grenzen

## Nächste Verbesserungen
```

---

# Troubleshooting-Pflichtpunkte

Dokumentiere mindestens:

## Python-Version

```bash
python3 --version
```

Projekt erwartet Python >=3.11.

## Virtuelle Umgebung

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Submodule

```bash
git submodule update --init --recursive
```

## Playwright

Falls Playwright-Tests optional sind:

```bash
python -m playwright install
```

Nur dokumentieren, nicht zwingend in `ci-local` aufnehmen, falls nicht nötig.

## Docker/SearXNG

Nur optional für echte Laufzeit-Recherche.

## Ollama

Nur optional für echte lokale LLM-Runtime.

## Tor

Nur optional für Onion/Darknet-Live-Funktionen.

---

# Validierung

Nach Doku-/Makefile-/README-Änderungen ausführen:

```bash
make quality
make coverage
make test-e2e
make ci-local
```

Optional:

```bash
make ci-full
```

Zusätzlich im Fresh Clone, falls möglich, denselben Satz ausführen.

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Fresh-Clone-Pfad getestet oder sauber simuliert wurde
- README enthält copy-paste-fähigen Quickstart
- `docs/development/fresh-clone-onboarding.md` existiert
- `make quality` im dokumentierten Pfad grün ist
- `make coverage` im dokumentierten Pfad grün ist
- `make test-e2e` im dokumentierten Pfad grün ist
- `make ci-local` im dokumentierten Pfad grün ist
- externe Dienste als optional dokumentiert sind
- Troubleshooting-Abschnitt existiert
- keine produktive Logik geändert wurde
- keine Quality Gates gelockert wurden
- GitHub-Kommentar mit Fresh-Clone-Ergebnis geschrieben wurde

Minimal akzeptabel:

- Fresh-Clone-Doku vorhanden
- Quickstart im README
- `make ci-local` reproduzierbar
- externe Dienste nicht versehentlich als Pflicht

Gut:

- echter Fresh Clone erfolgreich getestet
- Laufzeiten dokumentiert
- typische Fehler dokumentiert

Sehr gut:

- ein neuer Entwickler kann von null bis grüne Gates in unter 10 Minuten kommen
- README, docs/testing und docs/development sind konsistent verlinkt
- `make help` zeigt den empfohlenen Onboarding-Pfad

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Fresh-Clone-Onboarding Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Fresh-Clone-Test durchgeführt | |
| README Quickstart aktualisiert | |
| Fresh-Clone-Doku erstellt | |
| `make quality` grün | |
| `make coverage` grün | |
| `make test-e2e` grün | |
| `make ci-local` grün | |
| Optionale Dienste dokumentiert | |
| Troubleshooting dokumentiert | |
| Keine produktive Logik geändert | |
| Keine Quality Gates gelockert | |
| GitHub-Kommentar geschrieben | |

## Getestete Umgebung

| Feld | Wert |
|---|---|
| OS | |
| Python | |
| pip | |
| Branch | |
| Commit | |
| Docker | |
| GPU | |

## Fresh-Clone-Befehle

```bash
# exakte Befehle und Ergebnis
```

## Gate-Ergebnisse

| Befehl | Ergebnis | Laufzeit |
|---|---|---|
| make quality | | |
| make coverage | | |
| make test-e2e | | |
| make ci-local | | |
| make ci-full | | |

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
4. `Runtime smoke test: Ollama + SearXNG + Tor optional prüfen`
