# Issue Prompt: T-001

## Ziel
Git-Repository initialisieren, Python-Virtualenv anlegen, Abhängigkeiten installieren, `.env.example`-Vorlage erstellen, `.gitignore` konfigurieren.

## Kontext
Erster Issue des Projekts. Das Repository bei `https://github.com/xxammaxx/Researcher` ist bereits initialisiert und mit `main`-Branch versehen. Der Workspace enthält bereits OpenSpec-Artefakte und Dokumentation aus dem ersten Durchlauf (Planung).

## Betroffene Module
- `Infrastructure`

## Relevante Dateien
- `.gitignore`
- `.env.example`
- `requirements.txt`

## Architekturregeln
- `.env`-Datei MUSS in `.gitignore` stehen
- `.env.example` SOLL alle Umgebungsvariablen mit Kommentaren dokumentieren
- Python 3.12 als Zielversion
- `requirements.txt` SOLL alle Abhängigkeiten enthalten

## Best Practices
- `.env.example` mit Platzhalter-Werten, nicht mit echten Secrets
- `requirements.txt` mit gepinnten Versionen wo sinnvoll
- `.gitignore` nach https://github.com/github/gitignore (Python-Template)

## Akzeptanzkriterien
- **GIVEN** das Repository ist geklont **WHEN** `pip install -r requirements.txt` ausgeführt wird **THEN** sind alle Abhängigkeiten installiert.
- **GIVEN** `.env.example` existiert **WHEN** der Nutzer es nach `.env` kopiert **THEN** sind alle Variablen dokumentiert und kommentiert.

## Tests
- `pip install -r requirements.txt` (Exitcode 0)
- `.env.example` existiert und enthält alle Variablen aus `blueprint.md` Abschnitt 5

## Risiken
- 🟢 Niedrig – reine Konfigurationsarbeit, keine Abhängigkeiten
