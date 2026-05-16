# Issue Prompt: T-011

## Ziel
README.md mit vollständiger Setup-Anleitung, Betriebsanleitung (alle Terminal-Befehle für die 4 parallelen Prozesse), Troubleshooting-Guide für häufige Fehler, Changelog finalisieren.

## Kontext
Letzter Issue des Projekts. Alle Komponenten sind implementiert und getestet. Die Dokumentation muss einem neuen Nutzer ermöglichen, das System von Grund auf einzurichten.

## Betroffene Module
_Dokumentation_

## Relevante Dateien
- `README.md`
- `docs/troubleshooting.md`
- `docs/changelog/iteration-1.md` (finalisieren)

## Architekturregeln
- README MUSS Setup-Schritte enthalten (Ollama, Modell, SearXNG, GPT Researcher, Tor, Crawler)
- README MUSS das 4-Terminal-Layout dokumentieren
- Troubleshooting MUSS mindestens abdecken: Ollama nicht gestartet, SearXNG nicht erreichbar, VRAM-Überlauf, Tor nicht verfügbar
- Changelog MUSS alle Issues dieser Iteration referenzieren

## Best Practices
- README mit "Quick Start" Sektion für erfahrene Nutzer
- Code-Blöcke mit `bash`, `python`, `yaml` Sprachkennzeichnung
- Troubleshooting als FAQ-Struktur (Frage → Ursache → Lösung)
- Changelog nach https://keepachangelog.com (SemVer)

## Akzeptanzkriterien
- **GIVEN** ein neuer Nutzer folgt der README.md **WHEN** alle Setup-Schritte ausgeführt wurden **THEN** ist das System betriebsbereit und eine Test-Recherche liefert Ergebnisse.
- **GIVEN** das System zeigt einen Fehler (z.B. Ollama nicht gestartet) **WHEN** der Troubleshooting-Guide konsultiert wird **THEN** ist der Fehler dokumentiert und hat eine geprüfte Lösung.
- **GIVEN** eine Komponente wurde geändert **WHEN** das Changelog gelesen wird **THEN** sind alle Änderungen nachvollziehbar dokumentiert.

## Tests
- README.md auf Rechtschreibung und Formatierung prüfen
- Setup-Schritte sequenziell ausführen (frischer Clone) → System läuft
- Jeder Troubleshooting-Eintrag auf Korrektheit prüfen
- Changelog auf Vollständigkeit prüfen (alle 11 Issues)

## Risiken
- 🟢 Niedrig – reine Dokumentationsarbeit
