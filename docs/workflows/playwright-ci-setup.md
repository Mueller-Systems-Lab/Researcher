---
title: Playwright-CI-Setup
description: Kurzanleitung für den Playwright-Job in der GitHub-Actions-Umgebung.
---

# Playwright-CI-Setup

## Überblick

Der GitHub-Actions-Job `playwright` in `.github/workflows/test.yml` läuft auf `ubuntu-latest` und prüft die Playwright-Browser-Tests für das GPU-Dashboard. Er:

1. installiert Playwright,
2. lädt Chromium inkl. Systemabhängigkeiten,
3. führt `make playwright` aus (`python3 -m pytest tests/playwright/ -v`),
4. lädt bei Fehlern Artefakte hoch.

## Voraussetzungen

Für lokale Ausführung und CI braucht es:

- Python-Abhängigkeit `playwright`
- Browser-Installation: `playwright install chromium --with-deps`

Ohne Chromium schlagen die Browser-Tests fehl oder werden übersprungen.

## Artefakte

Bei einem Fehlschlag lädt CI folgende Pfade als Artefakt `playwright-artifacts` hoch:

- `tests/playwright/screenshots/`
- `tests/playwright/baselines/`

Typische Inhalte:

- Screenshots und HTML-Dumps unter `tests/playwright/screenshots/`
- Referenzbilder unter `tests/playwright/baselines/`

## Baselines aktualisieren

Baselines werden **nur manuell** aktualisiert, nie automatisch in CI.

Empfohlener Ablauf:

1. lokal die Playwright-Tests ausführen,
2. bewusste UI-Änderung prüfen,
3. neue Baseline-Dateien in `tests/playwright/baselines/` übernehmen,
4. Änderungen committen.

Wenn die Baseline unbeabsichtigt abweicht, erst die Ursache prüfen (Rendering, Daten, Browser-Version), dann entscheiden.

## Troubleshooting

| Problem | Ursache | Lösung |
|---|---|---|
| Chromium fehlt | `playwright install chromium --with-deps` wurde nicht ausgeführt | Playwright + Chromium neu installieren |
| GPU nicht verfügbar | Dashboard-Daten sind leer oder der Test fällt auf Fallbacks zurück | Lokalen GPU-/Dashboard-Stack prüfen; im CI ist kein echtes GPU-Setup garantiert |
| Rendering-Abweichungen | Unterschiedliche Fonts, Browser-Versionen oder Timing | Screenshot erneut lokal prüfen und Baseline nur bei absichtlicher Änderung anpassen |

## Kurzbefehle

```bash
pip install playwright
playwright install chromium --with-deps
make playwright
```
