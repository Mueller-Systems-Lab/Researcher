# Integrationsplan

## Metadaten
- **Erstellt:** 2026-05-16
- **Basiert auf:** design.md, tasks.md, docs/dependency-graph.md

## Integrationsstrategie: Vertikale Slices

Jedes Issue wird als vertikaler Slice implementiert – von der Code-Änderung über Tests bis zur Dokumentation. Kein Issue ist abgeschlossen, bevor es vollständig vertikal integriert ist.

## Integrationswellen

### Welle 1: Infrastruktur (4 Issues parallel)
```
T-001: Repository & Basis-Umgebung ────┐
T-002: Ollama + LLM ────────────────────┤
T-003: SearXNG Docker ──────────────────┤─── Welle 1 abgeschlossen
T-005: Darknet-Crawler ─────────────────┘
```

**Integrationscheck:**
- [ ] Git-Repository initialisiert
- [ ] Ollama läuft mit unzensiertem Modell
- [ ] SearXNG liefert JSON-Ergebnisse
- [ ] Darknet-Crawler extrahiert Posts über Tor

### Welle 2: Framework-Integration (2 Issues)
```
T-004: GPT Researcher konfigurieren ─┐
T-006: DarknetRetriever ─────────────┤─── Welle 2 abgeschlossen
T-009: VRAM-Tuning ──────────────────┘
```

**Integrationscheck:**
- [ ] GPT Researcher startet mit lokaler Konfiguration
- [ ] DarknetRetriever liefert Suchergebnisse aus Whoosh
- [ ] VRAM unter 7.5 GB unter Last

### Welle 3: Composite + Vektor (2 Issues)
```
T-007: CompositeRetriever ────────────┐
T-008: ChromaDB + Embeddings ─────────┤─── Welle 3 abgeschlossen
```

**Integrationscheck:**
- [ ] CompositeRetriever merged Web + Darknet-Ergebnisse
- [ ] Deduplizierung funktioniert
- [ ] ChromaDB speichert und liefert Embeddings
- [ ] Embeddings werden auf CPU berechnet

### Welle 4: Validierung (1 Issue)
```
T-010: Integrationstests ──────────────── Welle 4 abgeschlossen
```

**Integrationscheck:**
- [ ] End-to-End-Test erfolgreich
- [ ] Fehlertoleranz-Tests bestanden
- [ ] VRAM-Monitoring zeigt < 7.5 GB

### Welle 5: Dokumentation (1 Issue)
```
T-011: Dokumentation ───────────────────── System bereit
```

## Integrations-Testmatrix

| Testfall | Beteiligte Module | Akzeptanz |
|---|---|---|
| **E2E-01:** Recherche mit Web-Quellen | Orchestrator → SearXNG → LLM | Report enthält Web-Zitate |
| **E2E-02:** Recherche mit Darknet-Quellen | Orchestrator → DarknetRetriever → LLM | Report enthält Darknet-Zitate |
| **E2E-03:** Parallele Recherche (beide Quellen) | CompositeRetriever → SearXNG + Darknet | Ergebnisse dedupliziert |
| **E2E-04:** Wissensspeicherung | Orchestrator → ChromaDB | Embeddings persistiert |
| **E2E-05:** Wissensabruf | Orchestrator → ChromaDB | Relevante Embeddings gefunden |
| **FT-01:** SearXNG down → Fallback | CompositeRetriever → DarknetRetriever | Nur Darknet-Ergebnisse |
| **FT-02:** Darknet-Index leer → Fallback | CompositeRetriever → SearXNG | Nur Web-Ergebnisse |
| **FT-03:** ChromaDB down | Orchestrator → Fallback | System läuft ohne Vektor-Speicher |
| **VRAM-01:** LLM + Embedding parallel | LLM + Embedding | VRAM < 7.5 GB |

## Rollback-Strategie

Jedes Issue wird auf einem eigenen Branch entwickelt und per PR gemerged:
- `issue/001-repo-setup`
- `issue/002-ollama-llm`
- `issue/003-searxng`
- ...

Bei Fehlern: Branch verwerfen oder revertieren. `main` bleibt stabil.
