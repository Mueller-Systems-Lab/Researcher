# Researcher — Nächstes Issue: Release Readiness — Version, Changelog, Known Limitations

## Rolle

Du bist ein Senior Release Engineer, Technical Product Steward und Local-First OSS Maintainer.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Qualitäts- und Runtime-Chain:

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
- #67: Regression Guard
- #68: Security Regression Tests

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, den erreichten technischen Zustand als Release-fähigen Meilenstein zu dokumentieren und reproduzierbar abzusichern.

---

# Ausgangslage

Nach #68 existiert ein vollständiges lokales Qualitätssystem:

```bash
make quality
```

läuft als 6-in-1 Gate:

- lint / ruff: 0 Errors
- typecheck / mypy: 0 Projektfehler
- security-project / bandit: 0 Medium/High im Projektcode
- security-regression: 14 passed
- test-fast: 255 passed
- coverage: ca. 78.5%

Zusätzlich existieren:

- `make runtime-smoke`
- `make research-happy-path`
- `make research-evaluate`
- `make research-evaluate-multi`
- `make research-evaluate-regression`
- Fresh-Clone-Onboarding
- SearXNG Runtime-Doku
- Ollama Model-Konfiguration
- Report-Quality-Evaluation
- Security-Gate-Policy
- Security-Regression-Tests

Jetzt fehlt:

> Ein klarer Release-/Milestone-Stand: Was kann das System, was kann es bewusst noch nicht, wie wird es geprüft, wie wird es gestartet, und welche Risiken sind bekannt?

---

# Oberstes Ziel dieses Issues

Erstelle einen Release-Readiness-Meilenstein für den aktuellen Stand.

Der Meilenstein soll beantworten:

1. Welche Version / welcher Milestone ist dieser Stand?
2. Welche Befehle müssen grün sein?
3. Welche Runtime-Dienste sind optional oder erforderlich?
4. Was ist der validierte Happy-Path?
5. Welche Evaluationswerte sind bekannt?
6. Welche Security-Gates existieren?
7. Welche Limitations sind bewusst offen?
8. Welche Folge-Issues sind sinnvoll?
9. Wie kann ein Nutzer das System frisch klonen, prüfen und ausführen?

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik ändern
- Quality Gates lockern
- Coverage-Schwelle senken
- Tests löschen
- Security-Ausnahmen erweitern
- Cloud-Provider aktivieren
- Darknet-/Security-Recherche automatisieren
- Playwright-CI lösen, falls das ein eigenes Issue bleibt
- Vendor-Code ändern

---

# Release-Readiness-Prinzipien

## 1. Ehrlicher Release

Der Release-Stand soll nicht übertreiben.

Dokumentiere klar:

- validiert
- optional
- experimentell
- bekannt offen
- nicht im Scope

## 2. Reproduzierbarkeit

Jede Behauptung muss über einen Befehl, eine Datei oder einen dokumentierten Testpfad belegbar sein.

## 3. Local-First

Release-Doku muss klarstellen:

- keine Cloud-Provider nötig
- lokale Dienste: Ollama, SearXNG, Tor
- Cloud-Fallbacks blockiert
- Runtime-Checks vorhanden

## 4. Keine Feature-Erweiterung

Release Readiness ist Dokumentation, Packaging, Versionierung und Prüfbarkeit, nicht Produktfeaturebau.

---

# Arbeitsreihenfolge

## 1. Aktuellen Zustand reproduzieren

Führe aus:

```bash
git status --short
git rev-parse --short HEAD
make quality
make coverage
make test-e2e
make ci-local
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
make research-evaluate-regression
```

Optional:

```bash
make ci-full
```

Dokumentiere:

- Commit
- Branch
- Laufzeiten
- Testzahlen
- Coverage
- Evaluation Scores
- Runtime-Smoke-Ergebnis
- Report-Pfad
- Security-Gate-Ergebnis

---

## 2. Version/Milestone festlegen

Prüfe vorhandene Versionierung:

```text
pyproject.toml
README.md
CHANGELOG.md
docs/
```

Falls keine Version existiert, schlage einen internen Milestone vor:

```text
v0.1.0-local-research-alpha
```

oder:

```text
Milestone: Local Research Alpha
```

Empfohlen:

- noch kein „Stable“
- eher `alpha`, weil Reportqualität und Runtime-Pfade vorhanden sind, aber echte Produktreife noch wachsen muss

Mögliche Semantik:

```text
v0.1.0-local-alpha
```

Bedeutung:

- lokaler End-to-End-Happy-Path validiert
- Quality Gates grün
- keine Cloud-Provider
- Report-Quality-Evaluation vorhanden
- noch keine breite Real-World-Research-Validierung

---

## 3. CHANGELOG erstellen oder aktualisieren

Erstelle oder aktualisiere:

```text
CHANGELOG.md
```

Pflichtstruktur:

```markdown
# Changelog

## [v0.1.0-local-alpha] - YYYY-MM-DD

### Added

### Changed

### Fixed

### Security

### Testing

### Documentation

### Known Limitations
```

Inhalte aus #50–#68 zusammenfassen, aber nicht zu lang.

---

## 4. Release Notes erstellen

Erstelle:

```text
docs/release/v0.1.0-local-alpha.md
```

Pflichtinhalt:

```markdown
# Release Notes — v0.1.0-local-alpha

## Summary

## What Works

## Validated Commands

| Command | Status | Purpose |
|---|---|---|

## Runtime Requirements

| Service | Required For | Status |
|---|---|---|
| Ollama | Summary/Embeddings | |
| SearXNG | Local Search | |
| Tor | Optional Onion runtime | |

## Quality Gates

## Security Gates

## Research Evaluation

## Known Limitations

## Not in Scope

## Upgrade/Setup Notes

## Next Milestones
```

---

## 5. Known Limitations dokumentieren

Erstelle oder aktualisiere:

```text
docs/release/known-limitations.md
```

Mögliche Inhalte:

- Multi-Query Evaluation bisher harmlose Standardqueries
- Evaluation ist heuristisch, keine Wahrheitserkennung
- kein Cloud-Judge
- kein Produktiv-Darknet-Crawl
- SearXNG braucht lokalen Docker-Dienst
- Ollama-Modelle müssen lokal vorhanden sein
- Tor optional, nicht für alle Tests erforderlich
- Playwright-CI noch nicht vollständig finalisiert
- Vendor/Submodul-Findings sind report-only/Policy-basiert
- Reportqualität hängt von Suchergebnissen und lokalem Modell ab
- keine Garantie für faktische Wahrheit, nur Evidence-/Traceability-Heuristiken

---

## 6. README aktualisieren

README soll klar zeigen:

```markdown
## Current Status

Local Research Alpha.

## Quick Verification

```bash
make quality
make coverage
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
```

## What This Proves

## What This Does Not Prove

## Next Steps
```

Keine langen Details, nur klare Verlinkung auf Release Notes und Doku.

---

## 7. Release-Checkliste erstellen

Erstelle:

```text
docs/release/release-checklist.md
```

Pflichtinhalt:

```markdown
# Release Checklist

## Pre-Release

- [ ] Working tree clean
- [ ] make quality
- [ ] make coverage
- [ ] make ci-local
- [ ] runtime-smoke
- [ ] research-happy-path
- [ ] research-evaluate
- [ ] regression guard
- [ ] docs updated
- [ ] changelog updated

## Optional

- [ ] make ci-full
- [ ] multi-query live validation
- [ ] Playwright checks
- [ ] upstream security PR review

## Release Tag

```bash
git tag v0.1.0-local-alpha
git push origin v0.1.0-local-alpha
```

Do not tag automatically unless explicitly requested.
```

Wichtig:

- Tag-Befehl nur dokumentieren.
- Nicht automatisch taggen, außer Nutzer verlangt es.

---

## 8. Optional: GitHub Milestone/Issue-Kommentar

Falls GitHub CLI verfügbar und erlaubt ist:

- GitHub-Kommentar zu aktuellem Issue schreiben
- keine Releases/tags automatisch erstellen
- optional Milestone-Vorschlag dokumentieren

---

# Validierung

Nach Änderungen ausführen:

```bash
make quality
make coverage
make test-e2e
make ci-local
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
make research-evaluate-regression
```

Optional:

```bash
make ci-full
```

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Release-Version/Milestone definiert ist
- CHANGELOG.md existiert oder aktualisiert ist
- Release Notes existieren
- Known Limitations dokumentiert sind
- Release Checklist existiert
- README Current Status/Quick Verification aktualisiert ist
- validierte Befehle dokumentiert sind
- Quality-Gates weiterhin grün sind
- Runtime-Smoke weiterhin grün ist oder Status dokumentiert ist
- Research-Happy-Path weiterhin grün ist
- Research-Evaluation weiterhin grün ist
- keine produktive Logik geändert wurde
- keine Gates gelockert wurden
- keine Cloud-Provider eingeführt wurden
- GitHub-Kommentar geschrieben wurde

Minimal akzeptabel:

- CHANGELOG
- Release Notes
- Known Limitations
- Release Checklist
- README-Status
- keine Regression

Gut:

- alle Validierungsbefehle mit Ergebnissen dokumentiert
- Release-Doku ist Fresh-Clone-kompatibel
- klare nächste Milestones

Sehr gut:

- Projekt ist bereit für einen manuell gesetzten `v0.1.0-local-alpha` Tag

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Release Readiness Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Version/Milestone definiert | |
| CHANGELOG aktualisiert | |
| Release Notes erstellt | |
| Known Limitations dokumentiert | |
| Release Checklist erstellt | |
| README aktualisiert | |
| Validierte Befehle dokumentiert | |
| `make quality` grün | |
| `make coverage` grün | |
| `make ci-local` grün | |
| Runtime-Smoke grün/dokumentiert | |
| Research-Happy-Path grün | |
| Research-Evaluation grün | |
| Keine produktive Logik geändert | |
| Keine Gates gelockert | |
| GitHub-Kommentar geschrieben | |

## Milestone

## Validierte Befehle

| Befehl | Ergebnis | Laufzeit |
|---|---|---|

## Geänderte Dateien

## Known Limitations

## Nächste Milestones

## Bewusst nicht durchgeführt

## Risiken
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Playwright-CI-Strategie definieren`
2. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
3. `Research Evaluation Dataset: harmlose Query-Fixtures versionieren`
4. `Optional: v0.1.0-local-alpha Git Tag und GitHub Release erstellen`
