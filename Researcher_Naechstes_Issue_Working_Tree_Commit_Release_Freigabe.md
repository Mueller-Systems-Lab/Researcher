# Researcher — Nächstes Issue: Working Tree bereinigen, Release-Artefakte committen und Tag/Release-Freigabe vorbereiten

## Rolle

Du bist ein Senior Release Engineer, Git Safety Agent und GitHub Release Steward.

Du arbeitest im Repository `xxammaxx/Researcher` auf Basis der abgeschlossenen Release-Vorbereitung zu `v0.1.0-local-alpha`.

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, den aktuellen Release-Kandidaten sicher in Git zu persistieren, den Working Tree zu bereinigen und danach die kontrollierte Tag-/GitHub-Release-Freigabe vorzubereiten.

---

# Ausgangslage

Release-Vorbereitung abgeschlossen:

- Release-Artefakte geprüft: ✅
- Finale Gates dokumentiert: ✅
- Release Candidate Summary erstellt: ✅
- GitHub Release Notes erstellt: ✅
- Tag `v0.1.0-local-alpha` existiert nicht: ✅
- GitHub Release existiert nicht: ✅
- Tag-/Release-Befehle vorbereitet: ✅
- Keine automatische Veröffentlichung: ✅
- Keine produktive Logik geändert: ✅
- GitHub-Kommentar auf #70 geschrieben: ✅

Final validierter Stand:

| Befehl | Ergebnis |
|---|---|
| `make quality` | ✅ 255 passed, 0 Errors |
| `make coverage` | ✅ 78.52% |
| `make test-e2e` | ✅ 9 passed |
| `make ci-local` | ✅ All green |
| `SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke` | ✅ 4/4 Dienste |
| `ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path` | ✅ Report erzeugt |
| `make research-evaluate` | ✅ 99/100 |

Blocker:

```text
119 uncommitted changes.
```

Vor Tagging MUSS der Working Tree bereinigt werden.

---

# Oberstes Ziel dieses Issues

1. Working Tree vollständig prüfen.
2. Änderungen kategorisieren.
3. Sicherstellen, dass keine unerwarteten produktiven Änderungen enthalten sind.
4. Finale Gates erneut ausführen oder vorhandene frische Ergebnisse bestätigen.
5. Release-Artefakte committen.
6. Branch pushen.
7. Tag-/GitHub-Release-Freigabe vorbereiten.
8. Tag/Release NICHT ohne explizite Freigabe ausführen.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- produktive Logik ändern
- Quality Gates lockern
- Tests löschen
- Coverage-Schwelle senken
- Release taggen ohne explizite Freigabe
- GitHub Release veröffentlichen ohne explizite Freigabe
- uncommitted Änderungen blind committen, ohne sie vorher zu klassifizieren
- Branches wechseln oder rebasen, ohne ausdrückliche Freigabe

---

# Arbeitsreihenfolge

## 1. Working Tree analysieren

Führe aus:

```bash
git status --short
git diff --stat
git diff --name-status
git rev-parse --short HEAD
git branch --show-current
```

Dokumentiere:

- Branch
- Commit
- Anzahl geänderter Dateien
- neue Dateien
- gelöschte Dateien
- produktive Code-Dateien
- Test-Dateien
- Doku-Dateien
- Report-/Artefakt-Dateien
- ungewollte Laufzeit-Artefakte

Besonders prüfen:

```text
reports/
.venv/
__pycache__/
.pytest_cache/
.coverage
*.log
.env
```

Diese Dateien dürfen normalerweise NICHT committed werden, außer bewusst dokumentiert.

---

## 2. Änderungen kategorisieren

Erstelle Tabelle:

```markdown
| Kategorie | Dateien | Committen? | Begründung |
|---|---:|---|---|
| Release-Doku | | Ja | |
| README/CHANGELOG | | Ja | |
| Tests | | Ja, falls Teil der Chain | |
| Makefile/CI | | Ja, falls validiert | |
| Runtime-Skripte | | Ja, falls Teil der Chain | |
| Generated Reports | | Nein/prüfen | |
| Cache/Temp | | Nein | |
| Secrets/.env | | Nein | |
```

Wenn `.env` oder Secrets auftauchen:

- sofort stoppen
- nicht committen
- `.gitignore` prüfen

---

## 3. Gitignore prüfen

Führe aus:

```bash
git check-ignore -v reports/* 2>/dev/null || true
git check-ignore -v .env 2>/dev/null || true
git check-ignore -v .coverage 2>/dev/null || true
```

Wenn Laufzeit-Artefakte nicht ignoriert werden:

- `.gitignore` minimal ergänzen
- Änderung dokumentieren

---

## 4. Finale Validierung vor Commit

Wenn der Diff plausibel ist, führe mindestens aus:

```bash
make quality
make coverage
make ci-local
```

Optional, falls Runtime verfügbar:

```bash
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
```

Wenn ein Gate fehlschlägt:

- nicht committen
- Fehler dokumentieren
- minimal reparieren oder abbrechen

---

## 5. Commit vorbereiten

Wenn alles sauber ist:

```bash
git add -A
git status --short
git diff --cached --stat
```

Prüfe erneut:

- keine `.env`
- keine Secrets
- keine Cache-Dateien
- keine ungewollten Reports
- keine unerwarteten großen Dateien

Dann committen:

```bash
git commit -m "release: prepare v0.1.0-local-alpha"
```

---

## 6. Push vorbereiten und ausführen

Nach Commit:

```bash
git status --short
git log --oneline -3
git push origin qa/accessibility-tests
```

Wenn Push fehlschlägt:

- Fehler dokumentieren
- nicht taggen
- keine Force-Pushes ohne Freigabe

---

## 7. Nach Commit erneut Tag-Status prüfen

```bash
git tag --list "v0.1.0-local-alpha"
gh release view v0.1.0-local-alpha || true
```

Dokumentiere:

- Tag existiert?
- GitHub Release existiert?
- aktueller Commit für Tag-Kandidat

---

## 8. Tag-/Release-Freigabe vorbereiten

Nur vorbereiten, nicht automatisch ausführen:

```bash
git tag -a v0.1.0-local-alpha -m "v0.1.0-local-alpha: Local Research Alpha"
git push origin v0.1.0-local-alpha
```

```bash
gh release create v0.1.0-local-alpha \
  --title "v0.1.0-local-alpha — Local Research Alpha" \
  --notes-file docs/release/github-release-notes-v0.1.0-local-alpha.md
```

Vor Ausführung muss explizit gefragt werden:

```text
Soll ich den Tag und GitHub Release jetzt erstellen? Antworte exakt mit:
FREIGABE TAG UND RELEASE
```

Ohne diese Freigabe:

- keine Tag-Erstellung
- kein GitHub Release

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- Working Tree analysiert wurde
- uncommitted Änderungen kategorisiert wurden
- keine Secrets oder Cache-Dateien committed wurden
- finale Gates vor Commit grün waren
- Release-Artefakte committed wurden
- Branch gepusht wurde
- Working Tree danach sauber ist
- Tag-Existenz erneut geprüft wurde
- GitHub-Release-Existenz erneut geprüft wurde
- Tag-/Release-Befehle vorbereitet wurden
- keine automatische Veröffentlichung ohne Freigabe erfolgt ist
- GitHub-Kommentar geschrieben wurde

Minimal akzeptabel:

- Working Tree bereinigt
- Commit + Push erfolgt
- Tag/Release vorbereitet, aber nicht ausgeführt

Gut:

- Commit enthält nur erwartete Release-/Quality-Artefakte
- Validierung nach Commit dokumentiert
- Release kann direkt freigegeben werden

Sehr gut:

- Nach expliziter Freigabe wurde Tag + GitHub Release erstellt und Post-Release-Checkliste abgearbeitet

---

# Abschlussbericht-Vorlage

```markdown
# Researcher Release Commit / Working Tree Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Working Tree analysiert | |
| Änderungen kategorisiert | |
| Secrets ausgeschlossen | |
| Cache/Reports ausgeschlossen | |
| Finale Gates grün | |
| Commit erstellt | |
| Branch gepusht | |
| Working Tree sauber | |
| Tag-Existenz geprüft | |
| GitHub Release-Existenz geprüft | |
| Tag/Release vorbereitet | |
| Keine Veröffentlichung ohne Freigabe | |
| GitHub-Kommentar geschrieben | |

## Commit

| Feld | Wert |
|---|---|
| Branch | |
| Vorheriger Commit | |
| Neuer Commit | |
| Commit Message | |

## Geänderte Dateien nach Kategorie

| Kategorie | Anzahl | Bemerkung |
|---|---:|---|

## Validierte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Tag-Status

## GitHub-Release-Status

## Freigabe erforderlich

Tag und GitHub Release wurden noch nicht erstellt.

Zur Veröffentlichung muss explizit freigegeben werden:

```text
FREIGABE TAG UND RELEASE
```

## Nächste Schritte
```

---

# Empfohlenes nächstes Folge-Issue nach Abschluss

Nach diesem Issue sollte eines dieser Issues folgen:

1. `Tag + GitHub Release nach Freigabe veröffentlichen`
2. `Post-Release Verification für v0.1.0-local-alpha`
3. `Playwright-CI-Strategie definieren`
4. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
