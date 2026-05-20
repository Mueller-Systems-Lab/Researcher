# Researcher — Nächstes Issue: v0.1.0-local-alpha Git Tag und GitHub Release kontrolliert erstellen

## Rolle

Du bist ein Senior Release Engineer, GitHub Release Manager und Local-First OSS Maintainer.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Chain:

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
- #60: SearXNG Runtime
- #61: Happy Path
- #62: Ollama Config
- #63: Report Eval
- #64: Report Traceability
- #65: Source Coverage
- #66: Multi-Query Eval
- #67: Regression Guard
- #68: Security Regression
- #69: Release Readiness

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, den in #69 dokumentierten Stand `v0.1.0-local-alpha` kontrolliert als Git-Tag und optional als GitHub Release vorzubereiten oder zu erstellen.

---

# Ausgangslage

Nach #69 ist `v0.1.0-local-alpha` release-fähig dokumentiert.

Validierter Zustand:

```bash
make quality
make runtime-smoke
make research-happy-path
make research-evaluate
```

Ergebnis:

- ruff: 0 Errors
- mypy: 0 Projektfehler
- bandit/security-project: 0 Medium/High
- security-regression: 14 passed
- test-fast: 255 passed
- coverage: ca. 78.5%
- runtime-smoke: 4/4 Dienste
- research-happy-path: Report erzeugt
- research-evaluate: 99/100
- Release Notes vorhanden
- Known Limitations vorhanden
- Release Checklist vorhanden
- CHANGELOG vorhanden
- README aktualisiert

---

# Oberstes Ziel dieses Issues

Erstelle einen kontrollierten Release-Prozess für `v0.1.0-local-alpha`.

Das Issue soll:

1. finalen Arbeitsbaum prüfen
2. finale Gates ausführen
3. Release-Dokumente prüfen
4. Tag-Entscheidung vorbereiten
5. Git-Tag nur nach expliziter Freigabe erstellen
6. GitHub Release nur nach expliziter Freigabe erstellen
7. Release-Notes aus vorhandener Doku übernehmen
8. Post-Release-Checks dokumentieren

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik ändern
- Quality Gates lockern
- Coverage-Schwelle senken
- Tests löschen
- neue Security-Ausnahmen einführen
- Cloud-Provider aktivieren
- automatisch taggen ohne explizite Freigabe
- automatisch GitHub Release veröffentlichen ohne explizite Freigabe
- Versionen blind ändern, ohne Release-Doku abzugleichen

---

# Release-Prinzipien

## 1. Keine automatische Veröffentlichung ohne Freigabe

Tag und GitHub Release sind irreversible oder öffentlich sichtbare Schritte.

Deshalb:

- Tag-Befehl vorbereiten
- Release-Text vorbereiten
- Nutzerfreigabe einholen
- erst dann ausführen

## 2. Finaler Zustand muss sauber sein

Vor Tagging:

```bash
git status --short
make quality
make coverage
make ci-local
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
```

Optional:

```bash
make ci-full
make research-evaluate-regression
```

## 3. Release ist ehrlich

`v0.1.0-local-alpha` ist kein Stable-Release.

Es bedeutet:

- Local-first Research-Happy-Path validiert
- Quality Gates grün
- Runtime-Diagnose vorhanden
- Report-Evaluation vorhanden
- bekannte Grenzen dokumentiert
- keine breite Real-World-Research-Validierung

---

# Arbeitsreihenfolge

## 1. Release-Artefakte prüfen

Lies:

```text
CHANGELOG.md
README.md
docs/release/v0.1.0-local-alpha.md
docs/release/known-limitations.md
docs/release/release-checklist.md
pyproject.toml
```

Dokumentiere:

- Version/Milestone konsistent?
- Release Notes vorhanden?
- Known Limitations vorhanden?
- Quick Verification vorhanden?
- Changelog-Eintrag vorhanden?
- README verweist auf Release-Status?
- pyproject-Version vorhanden oder bewusst nicht gesetzt?

Wenn `pyproject.toml` eine Version enthält, prüfe Konsistenz.

Wenn keine Version vorhanden ist:

- dokumentiere, ob das akzeptiert ist
- optional vorschlagen, aber nicht erzwingen

---

## 2. Finale Validierung ausführen

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
```

Optional:

```bash
make ci-full
make research-evaluate-regression
```

Dokumentiere:

- Commit-Hash
- Branch
- Laufzeiten
- Ergebnisse
- offene Änderungen
- ob der Arbeitsbaum sauber ist

Wenn Arbeitsbaum nicht sauber ist:

- nicht taggen
- Änderungen dokumentieren
- erst committen/pushen lassen

---

## 3. Release Candidate Summary erstellen

Erstelle:

```text
docs/release/v0.1.0-local-alpha-release-candidate.md
```

Pflichtinhalt:

```markdown
# Release Candidate — v0.1.0-local-alpha

## Commit

## Branch

## Gate Results

| Command | Result |
|---|---|

## Runtime Results

## Research Evaluation

## Known Limitations

## Release Decision

## Tag Command

```bash
git tag -a v0.1.0-local-alpha -m "v0.1.0-local-alpha"
git push origin v0.1.0-local-alpha
```

## GitHub Release Command

```bash
gh release create v0.1.0-local-alpha \
  --title "v0.1.0-local-alpha" \
  --notes-file docs/release/v0.1.0-local-alpha.md
```

## Manual Approval Required

Tagging and release publishing require explicit approval.
```

---

# 4. GitHub Release Notes vorbereiten

Erstelle optional:

```text
docs/release/github-release-notes-v0.1.0-local-alpha.md
```

Kurz und veröffentlichungsgeeignet:

```markdown
# v0.1.0-local-alpha

Local-first research alpha release.

## Highlights

- Local research happy-path: Query → SearXNG → Ollama → Report
- 6-in-1 blocking quality gate
- Runtime smoke checks for Ollama, SearXNG, Tor and cloud-blocker
- Research report quality evaluation
- Multi-query regression guard
- Security regression tests

## Verification

```bash
make quality
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
```

## Known Limitations

See `docs/release/known-limitations.md`.
```

---

# 5. Tagging vorbereiten

Prüfe bestehenden Tag:

```bash
git tag --list "v0.1.0-local-alpha"
```

Wenn Tag existiert:

- nicht überschreiben
- dokumentieren
- neue Entscheidung erforderlich

Wenn Tag nicht existiert:

Bereite Befehl vor:

```bash
git tag -a v0.1.0-local-alpha -m "v0.1.0-local-alpha"
git push origin v0.1.0-local-alpha
```

Wichtig:

- Nicht ausführen ohne explizite Nutzerfreigabe.

---

# 6. GitHub Release vorbereiten

Prüfe GitHub CLI:

```bash
gh auth status
gh release view v0.1.0-local-alpha || true
```

Wenn Release existiert:

- nicht überschreiben
- dokumentieren

Wenn nicht:

Bereite Befehl vor:

```bash
gh release create v0.1.0-local-alpha \
  --title "v0.1.0-local-alpha" \
  --notes-file docs/release/github-release-notes-v0.1.0-local-alpha.md
```

Wichtig:

- Nicht ausführen ohne explizite Nutzerfreigabe.

---

# 7. Post-Release-Checkliste dokumentieren

Ergänze in `docs/release/release-checklist.md`:

```markdown
## Post-Release

- [ ] Tag exists on GitHub
- [ ] GitHub Release exists
- [ ] Release notes render correctly
- [ ] README status matches release
- [ ] Next milestone issues created
- [ ] Known limitations still linked
```

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- finale Release-Artefakte geprüft wurden
- finale Gates dokumentiert wurden
- Release Candidate Summary existiert
- GitHub Release Notes vorbereitet sind
- Tag-Existenz geprüft wurde
- GitHub Release-Existenz geprüft wurde
- Tag-Befehle dokumentiert sind
- GitHub-Release-Befehle dokumentiert sind
- keine automatische Veröffentlichung ohne Freigabe erfolgte
- Post-Release-Checkliste ergänzt wurde
- keine produktive Logik geändert wurde
- keine Gates gelockert wurden
- GitHub-Kommentar geschrieben wurde

Minimal akzeptabel:

- RC Summary
- Release Notes
- finale Gate-Ergebnisse
- Tag-/Release-Befehle vorbereitet
- keine automatische Veröffentlichung

Gut:

- `gh`-Status geprüft
- bestehende Tags/Releases geprüft
- Release kann mit einem manuellen Befehl veröffentlicht werden

Sehr gut:

- Nach expliziter Freigabe wurde Tag + GitHub Release erstellt und Post-Release-Check dokumentiert

---

# Abschlussbericht-Vorlage

```markdown
# Researcher v0.1.0-local-alpha Release Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Release-Artefakte geprüft | |
| Finale Gates dokumentiert | |
| Release Candidate Summary erstellt | |
| GitHub Release Notes erstellt | |
| Tag-Existenz geprüft | |
| GitHub Release-Existenz geprüft | |
| Tag vorbereitet | |
| GitHub Release vorbereitet | |
| Post-Release-Checklist ergänzt | |
| Keine automatische Veröffentlichung ohne Freigabe | |
| Keine produktive Logik geändert | |
| GitHub-Kommentar geschrieben | |

## Commit

## Branch

## Finale Validierung

| Befehl | Ergebnis |
|---|---|

## Release-Dateien

## Tag-Status

## GitHub-Release-Status

## Manuelle Freigabe erforderlich

## Nächste Schritte
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Optional: Tag + GitHub Release nach Freigabe veröffentlichen`
2. `Playwright-CI-Strategie definieren`
3. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
4. `Research Evaluation Dataset: harmlose Query-Fixtures versionieren`
