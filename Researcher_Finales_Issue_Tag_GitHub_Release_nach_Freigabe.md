# Researcher — Finales Issue: Tag + GitHub Release nach Freigabe veröffentlichen

## Rolle

Du bist ein Senior Release Engineer und GitHub Release Operator.

Du arbeitest im Repository `xxammaxx/Researcher`.

Dein Ziel ist NICHT, neue Features zu bauen.

Dein Ziel ist, nach expliziter Freigabe den vorbereiteten Release `v0.1.0-local-alpha` zu taggen, zu pushen, als GitHub Release zu veröffentlichen und danach zu verifizieren.

---

# Ausgangslage

Die Release-Vorbereitung ist abgeschlossen.

Aktueller Release-Kandidat:

| Feld | Wert |
|---|---|
| Branch | `qa/accessibility-tests` |
| Vorheriger Commit | `1cd7c9f` |
| Release Commit | `deb7d58` |
| Version | `v0.1.0-local-alpha` |
| Tag | existiert noch nicht |
| GitHub Release | existiert noch nicht |

Working Tree:

- 135 Änderungen wurden geprüft und committed.
- Commit `deb7d58` wurde auf `origin/qa/accessibility-tests` gepusht.
- Keine Secrets oder `.env` wurden committed.
- QA-/Runtime-Artefakte wurden über `.gitignore` ausgeschlossen.
- Nur ein dokumentierter Submodul-dirty-Marker bleibt als bekannter Zustand.

Finale Validierung vor Commit war grün:

| Befehl | Ergebnis |
|---|---|
| `make quality` | ✅ 255 passed, 0 Errors |
| `make coverage` | ✅ 78.52% |
| `make test-e2e` | ✅ 9 passed |
| `make ci-local` | ✅ All green |
| `SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke` | ✅ 4/4 Dienste |
| `ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path` | ✅ Report erzeugt |
| `make research-evaluate` | ✅ 99/100 |

---

# Harte Freigaberegel

Tag und GitHub Release dürfen NUR erstellt werden, wenn der Nutzer exakt freigegeben hat:

```text
FREIGABE TAG UND RELEASE
```

Wenn diese Freigabe nicht vorliegt:

- NICHT taggen
- NICHT pushen
- NICHT veröffentlichen
- nur den Freigabestatus melden

---

# Oberstes Ziel

Nach Freigabe:

1. Release Commit verifizieren.
2. Tag-Existenz erneut prüfen.
3. GitHub Release-Existenz erneut prüfen.
4. Annotated Git Tag erstellen.
5. Tag pushen.
6. GitHub Release erstellen.
7. Release anzeigen/verifizieren.
8. Post-Release-Checkliste abhaken.
9. GitHub-Issue-Kommentar schreiben.
10. Issues #69, #70 und #71 nur schließen, wenn Release erfolgreich erstellt und verifiziert wurde.

---

# Nicht-Ziele

Dieses Issue darf NICHT:

- neue Features implementieren
- Code ändern
- Doku ändern, außer Post-Release-Status falls nötig
- Gates lockern
- Tag überschreiben
- bestehendes Release überschreiben
- Force-Push ausführen
- Branch wechseln oder rebasen
- bei Fehlern „trotzdem“ veröffentlichen

---

# Schritt 1 — Freigabe prüfen

Prüfe zuerst, ob die Freigabe exakt vorliegt:

```text
FREIGABE TAG UND RELEASE
```

Wenn nicht:

```markdown
Release ist vorbereitet, aber nicht freigegeben. Bitte antworte exakt mit:

FREIGABE TAG UND RELEASE
```

Danach stoppen.

---

# Schritt 2 — Release Commit verifizieren

Nach Freigabe ausführen:

```bash
git branch --show-current
git rev-parse --short HEAD
git status --short
git log --oneline -3
```

Erwartung:

- Branch: `qa/accessibility-tests`
- HEAD: `deb7d58` oder ein späterer bewusst dokumentierter Release-Commit
- keine unerwarteten uncommitted Änderungen
- Submodul-dirty-Marker nur, wenn bereits dokumentiert und unkritisch

Wenn HEAD nicht `deb7d58` ist:

- prüfen, ob der neuere Commit bewusst ist
- nicht taggen, solange unklar

---

# Schritt 3 — Tag und Release erneut prüfen

```bash
git tag --list "v0.1.0-local-alpha"
gh release view v0.1.0-local-alpha || true
```

Wenn Tag existiert:

- nicht neu erstellen
- dokumentieren
- prüfen, auf welchen Commit der Tag zeigt:

```bash
git rev-list -n 1 v0.1.0-local-alpha
```

Wenn GitHub Release existiert:

- nicht überschreiben
- dokumentieren
- Release anzeigen

---

# Schritt 4 — Annotated Tag erstellen

Nur wenn Tag nicht existiert:

```bash
git tag -a v0.1.0-local-alpha -m "v0.1.0-local-alpha: Local Research Alpha"
```

Danach prüfen:

```bash
git show v0.1.0-local-alpha --no-patch
```

---

# Schritt 5 — Tag pushen

```bash
git push origin v0.1.0-local-alpha
```

Danach prüfen:

```bash
git ls-remote --tags origin v0.1.0-local-alpha
```

---

# Schritt 6 — GitHub Release erstellen

Nur wenn GitHub Release noch nicht existiert:

```bash
gh release create v0.1.0-local-alpha   --title "v0.1.0-local-alpha — Local Research Alpha"   --notes-file docs/release/github-release-notes-v0.1.0-local-alpha.md
```

Danach prüfen:

```bash
gh release view v0.1.0-local-alpha
```

---

# Schritt 7 — Post-Release Verification

Führe aus:

```bash
git tag --list "v0.1.0-local-alpha"
git ls-remote --tags origin v0.1.0-local-alpha
gh release view v0.1.0-local-alpha
```

Optional, wenn schnell verfügbar:

```bash
make quality
make coverage
```

---

# Schritt 8 — Post-Release-Dokumentation

Wenn Release erfolgreich ist, aktualisiere falls vorgesehen:

```text
docs/release/release-checklist.md
```

Ergänze oder hake ab:

```markdown
## Post-Release

- [x] Tag exists locally
- [x] Tag exists on GitHub
- [x] GitHub Release exists
- [x] Release notes render correctly
- [x] Known limitations linked
- [x] Release commit documented
```

Wenn diese Datei geändert wird:

```bash
git add docs/release/release-checklist.md
git commit -m "docs: record v0.1.0-local-alpha post-release verification"
git push origin qa/accessibility-tests
```

Wichtig:

- Dieser Post-Release-Commit ist nach dem Tag und gehört nicht mehr zum Tag selbst.
- Das ist akzeptabel, wenn klar dokumentiert.

---

# Schritt 9 — GitHub-Kommentar

Kommentiere auf #71 oder dem aktuellen Release-Issue:

```markdown
# v0.1.0-local-alpha Release veröffentlicht

## Ergebnis

| Kriterium | Status |
|---|---|
| Annotated Tag erstellt | ✅ |
| Tag zu origin gepusht | ✅ |
| GitHub Release erstellt | ✅ |
| Release verifiziert | ✅ |
| Release Notes verwendet | ✅ |

## Tag

`v0.1.0-local-alpha`

## Commit

`<commit>`

## Release

<GitHub Release URL>

## Post-Release Notes

<kurz>
```

---

# Schritt 10 — Issues schließen

Nur wenn Tag und GitHub Release erfolgreich verifiziert sind:

- #69 schließen
- #70 schließen
- #71 schließen

Falls ein Schritt fehlschlägt:

- Issues offen lassen
- Fehler dokumentieren
- nächsten minimalen Reparaturschritt vorschlagen

---

# Akzeptanzkriterien

Dieses Issue ist erfolgreich, wenn:

- explizite Freigabe lag vor
- Release Commit wurde geprüft
- Tag existierte vorher nicht
- GitHub Release existierte vorher nicht
- annotated tag wurde erstellt
- Tag wurde zu origin gepusht
- GitHub Release wurde erstellt
- Release wurde verifiziert
- Release-Kommentar wurde geschrieben
- keine neuen Features wurden gebaut
- keine Gates wurden gelockert
- keine Force-Pushes wurden ausgeführt
- Issues wurden nur nach erfolgreicher Verifikation geschlossen

---

# Abschlussbericht-Vorlage

```markdown
# Researcher v0.1.0-local-alpha Veröffentlichung Abschlussbericht

## Ergebnis

| Kriterium | Status |
|---|---|
| Freigabe erhalten | |
| Release Commit geprüft | |
| Tag lokal erstellt | |
| Tag zu origin gepusht | |
| GitHub Release erstellt | |
| Release verifiziert | |
| Post-Release-Checklist aktualisiert | |
| GitHub-Kommentar geschrieben | |
| Issues geschlossen | |
| Keine neuen Features | |
| Keine Force-Pushes | |

## Release

| Feld | Wert |
|---|---|
| Version | v0.1.0-local-alpha |
| Branch | |
| Commit | |
| Tag URL | |
| GitHub Release URL | |

## Ausgeführte Befehle

```bash
# exakte Befehle und Ergebnis
```

## Bewusst nicht durchgeführt

## Risiken / Hinweise

## Nächster Meilenstein
```

---

# Empfohlener nächster Meilenstein nach Release

Nach Veröffentlichung von `v0.1.0-local-alpha`:

1. `Post-Release Verification für v0.1.0-local-alpha`
2. `Playwright-CI-Strategie definieren`
3. `Upstream-PR für gpt_researcher Security-Hardening vorbereiten`
4. `v0.2.0-local-research-quality: echte Reportqualität mit Query-Fixtures`
