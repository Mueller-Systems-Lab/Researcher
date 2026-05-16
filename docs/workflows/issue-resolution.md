# Issue Resolution Workflow

## Metadaten
- **Erstellt:** 2026-05-16
- **Gültig für:** Alle Issues in diesem Projekt

## Workflow pro Issue

### 1. Start-Gate (vor jeder Arbeit)
1. `git fetch --all --prune`
2. `gh issue view <ISSUE> --repo xxammaxx/Researcher --comments`
3. Start-Kommentar auf GitHub posten (Template: siehe unten)
4. Branch erstellen: `issue/<id>-<kurzbeschreibung>`

### 2. Kontext laden
1. `blueprint.md` einlesen
2. `specs/delta-specs.md` einlesen
3. `design.md` einlesen
4. `tasks.md` einlesen (betroffener Task)
5. `docs/research/issue-<id>.md` prüfen/erstellen

### 3. Recherche (pro Issue)
1. Technologie-Dokumentation recherchieren
2. Best Practices identifizieren
3. Sicherheitsaspekte prüfen
4. Ergebnisse in `docs/research/issue-<id>.md` dokumentieren

### 4. Implementierung
1. Code gemäß Task-Beschreibung und Specs implementieren
2. Tests schreiben (Unit + Integration)
3. Akzeptanzkriterien (Given/When/Then) umsetzen

### 5. Validierung
1. `pytest` oder äquivalent ausführen
2. Akzeptanzkriterien manuell prüfen
3. VRAM-Monitoring (falls relevant)

### 6. Integriertes Review
1. Review-Prompt aus Issue-Kommentar befolgen
2. Review-Agent aufrufen
3. Review-Ergebnisse verarbeiten
4. Reparatur-Zyklus (falls nötig)

### 7. Verify & Archive
1. Delta-Specs syncen
2. Tests final ausführen
3. Dokumentation aktualisieren
4. Changelog-Eintrag in `docs/changelog/iteration-<n>.md`
5. Commit mit Konvention (`feat:`, `fix:`, etc.)
6. Push
7. Issue schließen (Kommentar mit Testergebnissen)

### 8. Kontext-Isolation
1. Zusammenfassung speichern
2. Aktiven Kontext löschen
3. Nur Artefakte des nächsten Issues laden

## Start-Kommentar Template
```markdown
## 🔵 Task Started

### Context
- Issue: #<NUMBER>
- Branch: issue/<id>-<name>
- Current commit: <COMMIT>
- Started at: <ISO8601>

### Understanding
<Zusammenfassung des Issue-Verständnisses>

### Planned Work
1. <Schritt>
2. <Schritt>
...

### Tests Planned
- <Test 1>
- <Test 2>
```

## Completion-Kommentar Template
```markdown
## 🟢 Task Completed

### Context
- Issue: #<NUMBER>
- Branch: issue/<id>-<name>
- Commit: <COMMIT>

### Changes
<Zusammenfassung der Änderungen>

### Files Changed
- <Datei 1>
- <Datei 2>

### Tests Run
- `pytest tests/test_<name>.py` ✅
- `ollama run qwen3-8b-uncensored "test"` ✅

### Result
<Pass/Fail Zusammenfassung>

### Blockers / Follow-ups
- <Offene Punkte>
```
