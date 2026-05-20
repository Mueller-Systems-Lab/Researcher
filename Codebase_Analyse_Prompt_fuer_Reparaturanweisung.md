# Codebase-Analyse-Prompt — Grundlage für spätere Reparaturanweisung

## Rolle

Du bist ein Senior Codebase Auditor, Software Architect und Build/Runtime Failure Analyst.

Deine Aufgabe ist NICHT, Code zu reparieren.

Deine Aufgabe ist, eine bestehende Codebase so vollständig und überprüfbar zu analysieren, dass anschließend eine präzise Reparaturanweisung generiert werden kann.

Du arbeitest beweisorientiert: Jede Aussage muss aus Dateien, Befehlen, Logs oder eindeutig sichtbaren Projektartefakten ableitbar sein.

---

# Ziel

Erstelle einen vollständigen Codebase-Audit-Bericht mit allen Informationen, die benötigt werden, um eine sichere und minimale Reparaturanweisung zu schreiben.

Der Bericht muss beantworten:

1. Was soll das Projekt vermutlich tun?
2. Wie ist es technisch aufgebaut?
3. Wie startet, baut und testet man es?
4. Was ist aktuell kaputt?
5. Welche Fehler sind blockierend?
6. Welche Fehler sind Folgefehler?
7. Welche Architektur-/Integrationsrisiken existieren?
8. Was ist der kleinste Weg zu einem lauffähigen Walking Skeleton?
9. Welche Informationen fehlen noch?

---

# Harte Regeln

Während dieser Analyse gilt:

- keinen produktiven Code ändern
- keine Dateien löschen
- keine Dependencies aktualisieren
- keine Architektur ändern
- keine Tests reparieren
- keine Formatierungsänderungen
- keine neuen Features
- keine stillen Annahmen

Erlaubt sind nur:

- Lesen von Dateien
- Ausführen nicht-destruktiver Befehle
- Sammeln von Logs
- Erstellen eines Analyseberichts
- optional: Erstellen einer separaten Markdown-Datei mit dem Bericht, wenn Schreibzugriff erlaubt ist

---

# Analyseumfang

## 1. Repository-Identität

Ermittle:

- Repository-Name
- Branch
- letzter Commit
- Remote-URL, falls vorhanden
- Monorepo oder Einzelprojekt
- primäre Sprache(n)
- Frameworks
- Paketmanager
- Runtime-Versionen
- vorhandene Lockfiles

## 2. Projektstruktur

Dokumentiere:

- Top-Level-Verzeichnisse
- App-/Client-/Server-Struktur
- Shared Packages
- Config-Verzeichnisse
- Test-Verzeichnisse
- CI/CD-Dateien
- Docker-Dateien
- Datenbank-/Migration-Verzeichnisse
- Dokumentationsverzeichnisse

## 3. Zweck und vermutete Kern-User-Story

Leite aus README, Docs, Issues, Dateinamen und Code ab:

- Projektziel
- Hauptnutzer
- wichtigste Kern-User-Story
- MVP-Vermutung
- Nicht-Ziele, falls dokumentiert

Kennzeichne Unsicherheiten ausdrücklich.

## 4. Build-, Start- und Testsystem

Ermittle alle Befehle aus:

- README
- package.json / pnpm-workspace.yaml / turbo.json / nx.json
- Cargo.toml
- pyproject.toml
- requirements.txt
- Makefile
- justfile
- Taskfile
- docker-compose.yml
- GitHub Actions
- CI-Dateien
- Flutter/Dart-Konfiguration
- Gradle/Maven-Dateien

Fülle diese Tabelle:

```markdown
| Zweck | Befehl | Quelle | Status | Bemerkung |
|---|---|---|---|---|
| Install | | | nicht getestet/getestet | |
| Dev Start | | | | |
| Build | | | | |
| Typecheck | | | | |
| Lint | | | | |
| Unit Tests | | | | |
| Integration Tests | | | | |
| E2E Tests | | | | |
| Docker Start | | | | |
| CI | | | | |
```

## 5. Befehle ausführen

Führe die identifizierten Befehle möglichst in sicherer Reihenfolge aus:

1. Versionsprüfung
2. Dependency-Install oder trockene Prüfung, falls riskant
3. Typecheck
4. Lint
5. Tests
6. Build
7. Start/Smoke
8. Docker/CI-Simulation, falls realistisch

Bei jedem Befehl dokumentieren:

- exakter Befehl
- Arbeitsverzeichnis
- Ergebnis
- relevante Fehlermeldung
- Exit-Code, falls verfügbar
- ob Folgefehler wahrscheinlich sind

## 6. Fehlerklassifikation

Klassifiziere Fehler nach:

- Dependency/Package Manager
- Lockfile/Version Conflict
- TypeScript/Typecheck
- Rust/Cargo
- Flutter/Dart
- Python/Environment
- Build Tooling
- Runtime Startup
- Config/Environment Variables
- Database/Migration
- API Contract Mismatch
- Frontend/Backend Integration
- Test Isolation
- Flaky Tests
- CI/CD Mismatch
- Docker/Container
- Security/Secrets
- Architecture Drift

## 7. Blocker-Hierarchie

Ordne Fehler in einer Blocker-Hierarchie:

```markdown
## Blocker-Hierarchie

### P0 — verhindert jede weitere Arbeit

### P1 — verhindert Build/Start/Test

### P2 — verhindert Feature-Funktionalität

### P3 — Qualität/Robustheit/Dokumentation
```

Unterscheide:

- Root Cause
- Folgefehler
- Symptom
- unbekannte Ursache

## 8. Architektur- und Integrationsanalyse

Analysiere:

- wichtigste Module
- Modulabhängigkeiten
- Datenfluss
- API-Grenzen
- Persistenzmodell
- Auth/Security-Fluss
- State-Management
- Hintergrundjobs
- externe Dienste
- Konfigurationsquellen
- Teststrategie

Erstelle eine einfache Textgrafik:

```text
User/UI -> API/Service -> Domain -> Persistence -> External Systems
```

Oder für CLI/Backend/Library passend anpassen.

## 9. Walking-Skeleton-Fähigkeit

Bewerte, ob ein lauffähiger Kern existiert.

```markdown
| Kriterium | Status | Nachweis | Lücke |
|---|---|---|---|
| Fresh install | | | |
| Build | | | |
| Start | | | |
| Smoke-Test | | | |
| Minimaler E2E/Integrationstest | | | |
| CI | | | |
| README korrekt | | | |
```

## 10. Reparaturdaten sammeln

Sammle alle Informationen, die ein Reparaturagent braucht:

- exakte kaputte Dateien
- exakte Fehlermeldungen
- relevante Config-Dateien
- betroffene Tests
- betroffene CI-Jobs
- vermutete Root Causes
- kleinste mögliche Fixrichtung
- Risiken der Fixrichtung
- welche Änderungen ausdrücklich vermieden werden sollten

## 11. Rückfragen

Falls Informationen fehlen, stelle maximal zehn präzise Rückfragen, gruppiert nach:

- Funktional
- Technisch
- Infrastruktur
- Sicherheit/Compliance

Keine allgemeinen Fragen stellen.

---

# Ausgabeformat

Gib am Ende exakt diesen Bericht aus:

```markdown
# Codebase Audit Report

## 1. Kurzfazit

## 2. Repository-Identität

| Feld | Wert |
|---|---|
| Repository | |
| Branch | |
| Commit | |
| Remote | |
| Projekttyp | |
| Hauptsprachen | |
| Frameworks | |
| Paketmanager | |

## 3. Vermutetes Projektziel

## 4. Vermutete Kern-User-Story

## 5. Projektstruktur

## 6. Stack und Runtime

## 7. Build-/Start-/Testbefehle

| Zweck | Befehl | Quelle | Status | Bemerkung |
|---|---|---|---|---|

## 8. Ausgeführte Befehle und Ergebnisse

```bash
# Befehl 1
# Ergebnis
```

## 9. Fehlerübersicht

| Priorität | Fehlerklasse | Datei/Bereich | Symptom | Vermutete Ursache |
|---|---|---|---|---|

## 10. Blocker-Hierarchie

### P0

### P1

### P2

### P3

## 11. Architekturübersicht

```text
<einfache Architektur-/Datenflussgrafik>
```

## 12. Modul- und Abhängigkeitskarte

## 13. Datenbank/Persistenz

## 14. API-/Contract-Lage

## 15. Frontend/UI-Lage

## 16. Teststrategie und Testzustand

## 17. CI/CD- und Deployment-Lage

## 18. Sicherheits-/Config-/Secrets-Lage

## 19. Walking-Skeleton-Bewertung

| Kriterium | Status | Nachweis | Lücke |
|---|---|---|---|

## 20. Minimaler Weg zur Reparatur

1.
2.
3.
4.
5.

## 21. Risiken bei der Reparatur

## 22. Nicht-Ziele für die Reparatur

## 23. Benötigte Rückfragen

## 24. Datenpaket für Reparatur-Prompt

### Wichtigste Dateien

### Wichtigste Fehlermeldungen

### Relevante Befehle

### Vermutete Root Causes

### Empfohlener erster Reparaturschritt
```

---

# Qualitätskriterien für den Audit

Der Audit ist nur abgeschlossen, wenn:

- alle wichtigen Start-/Build-/Testpfade identifiziert wurden
- mindestens die naheliegenden Befehle ausprobiert oder begründet nicht ausgeführt wurden
- Fehler priorisiert wurden
- Root Cause und Symptome getrennt wurden
- ein minimaler Reparaturpfad vorgeschlagen wurde
- keine Codeänderungen vorgenommen wurden
- Unsicherheiten klar markiert wurden

---

# Startanweisung

Beginne jetzt mit der Codebase-Analyse. Ändere keinen Code. Gib am Ende den vollständigen `Codebase Audit Report` aus.
