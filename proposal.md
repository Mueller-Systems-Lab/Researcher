# Proposal: Lokales, unzensiertes Research-System

## Metadaten
- **Status:** Draft
- **Erstellt:** 2026-05-16
- **Autor:** Issue Orchestrator (AI)
- **Blueprint:** blueprint.md

## Zusammenfassung

Aufbau eines vollständig lokalen und kostenfreien Recherche-Assistenten auf Basis
von GPT Researcher. Das System läuft auf einer NVIDIA GeForce GTX 1070 (8 GB VRAM),
nutzt ein unzensiertes LLM, integriert sowohl die öffentliche Websuche per
selbstgehostetem SearXNG als auch eine eigene Darknet-Forum-Suche und speichert
gelerntes Wissen in einer Vektordatenbank. Alle Komponenten sind Open Source und
laufen ohne externe API-Aufrufe.

## Motivation

- **Zensurfreiheit:** Kommerzielle LLM-Anbieter filtern Inhalte und verweigern
  bestimmte Recherche-Themen. Ein unzensiertes, lokales Modell umgeht diese Einschränkung.
- **Datenschutz:** Keine Daten verlassen das lokale System – Suchanfragen,
  Rechercheergebnisse und Embeddings bleiben vollständig unter eigener Kontrolle.
- **Kosteneffizienz:** Keine API-Kosten. Einmalige Hardware-Investition (GTX 1070).
- **Forschungstiefe:** Integration von Darknet-Quellen zusätzlich zur öffentlichen
  Websuche ermöglicht Recherchen in sonst unzugänglichen Informationsräumen.
- **Lernfähigkeit:** Vektordatenbank speichert und vernetzt gewonnenes Wissen
  über Recherche-Sessions hinweg.

## Ziele

1. GPT Researcher lokal zum Laufen bringen (Fork + Anpassungen)
2. Unzensiertes LLM (Qwen3.5-9B-Uncensored-HauhauCS-Aggressive) in Ollama bereitstellen
3. SearXNG als lokale Websuche-Engine integrieren
4. Darknet-Forum-Crawler mit Whoosh-Volltextindex entwickeln
5. CompositeRetriever für parallele Suche (Web + Darknet) implementieren
6. ChromaDB mit nomic-embed-text für Wissensspeicherung konfigurieren
7. VRAM-Optimierungen für 8 GB GTX 1070 durchführen
8. Integrationstests aller Komponenten
9. Dokumentation und Betriebsanleitung

## Nicht-Ziele (Out of Scope)

- Kein Produktivbetrieb auf Multi-GPU-Setups
- Keine Cloud-Deployment-Unterstützung
- Keine Benutzer-Authentifizierung (Single-User, localhost)
- Keine automatische rechtliche Prüfung von Darknet-Inhalten
- Kein Crawlen von JavaScript-lastigen Darknet-Seiten (nur statisches HTML)

## Risiken

| Risiko | Eintrittsw. | Auswirkung | Maßnahme |
|---|---|---|---|
| Modell nicht verfügbar (fiktiv) | Mittel | Hoch | Alternatives unzensiertes 7B-Modell wählen |
| VRAM-Überlauf bei langem Kontext | Mittel | Mittel | num_ctx auf 4096 begrenzen, MAX_CONCURRENT=1 |
| Darknet-Crawler von Forum geblockt | Hoch | Mittel | Crawl-Pausen, User-Agent-Rotation, Rate-Limiting |
| Rechtliche Probleme Darknet-Crawling | Mittel | Kritisch | Fachanwalt konsultieren, Wegwerf-Account, Isolation |
| SearXNG-Inkompatibilität mit GPT Researcher | Niedrig | Hoch | Version pinnen, Fallback auf direkte SearXNG-API |
| ChromaDB-Speicherüberlauf | Niedrig | Mittel | Persistente Speicherung auf Disk, regelmäßige Komprimierung |

## Akzeptanzkriterien (Gesamtsystem)

1. **GIVEN** die lokale Umgebung ist eingerichtet **WHEN** der Nutzer `python -m gpt_researcher` ausführt **THEN** startet die Web-UI und ist unter `http://localhost:8000` erreichbar.
2. **GIVEN** eine Recherche-Anfrage wurde gestellt **WHEN** die Recherche abgeschlossen ist **THEN** enthält der Report Zitate aus SearXNG und (falls relevant) aus dem Darknet-Index.
3. **GIVEN** das System läuft **WHEN** eine zweite Recherche zu einem verwandten Thema gestartet wird **THEN** werden relevante Embeddings aus der vorherigen Session in ChromaDB gefunden und referenziert.
4. **GIVEN** Ollama läuft parallel **WHEN** eine LLM-Anfrage gestellt wird **THEN** wird die GTX 1070 nicht überlastet (VRAM < 7.5 GB).
