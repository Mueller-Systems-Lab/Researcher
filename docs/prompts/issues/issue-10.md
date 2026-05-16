# Issue Prompt: T-010

## Ziel
Umfassende Integrationstests: CompositeRetriever (beide Backends), ChromaDB (Embeddings speichern + lesen), End-to-End-Test (Recherche mit Web + Darknet), VRAM-Monitoring, Fehlertoleranz-Tests (SearXNG down, Darknet-Index leer, Tor down, ChromaDB down).

## Kontext
Dies ist der Validierungs-Issue. Alle Kernkomponenten sind implementiert und müssen als Gesamtsystem getestet werden. Fehlertoleranz ist kritisch: das System muss bei Ausfall einzelner Komponenten graceful degraden.

## Betroffene Module
_Querschnittlich (alle Module)_

## Relevante Dateien
- `tests/test_composite_retriever.py`
- `tests/test_chromadb.py`
- `tests/test_e2e.py`
- `tests/test_fault_tolerance.py`
- `tests/conftest.py`

## Architekturregeln
- Tests MÜSSEN isoliert lauffähig sein (kein externer State)
- Fixtures für SearXNG, Darknet-Index, ChromaDB in `conftest.py`
- Fehlertoleranz-Tests: Komponente mocken/stoppen, Systemverhalten prüfen
- E2E-Test: Kompletten Recherche-Durchlauf simulieren

## Best Practices
- `pytest` mit `-v` für detaillierte Ausgabe
- `pytest --cov` für Coverage-Report
- Testmarker: `@pytest.mark.slow` für E2E-Tests
- `@pytest.mark.skipif(not tor_available, reason="Tor not running")` für Darknet-Tests
- Mock-Server für SearXNG in Unit-Tests (z.B. `responses` oder `httpx-mock`)

## Akzeptanzkriterien
- **GIVEN** alle Komponenten laufen **WHEN** ein End-to-End-Test durchgeführt wird **THEN** wird ein vollständiger Report mit Quellen aus SearXNG und Darknet generiert.
- **GIVEN** SearXNG ist gestoppt **WHEN** eine Recherche gestartet wird **THEN** werden nur Darknet-Quellen genutzt und eine Warnung ausgegeben.
- **GIVEN** der Darknet-Index ist leer **WHEN** eine Recherche gestartet wird **THEN** werden nur SearXNG-Quellen genutzt.
- **GIVEN** ChromaDB ist nicht erreichbar **WHEN** eine Recherche gestartet wird **THEN** wird die Recherche ohne Vektorspeicherung fortgesetzt.

## Tests
- `pytest tests/test_composite_retriever.py -v`
- `pytest tests/test_chromadb.py -v`
- `pytest tests/test_e2e.py -v -m slow`
- `pytest tests/test_fault_tolerance.py -v`
- `pytest tests/ --cov=. --cov-report=term`
- VRAM-Check nach Testlauf: `nvidia-smi`

## Risiken
- 🟡 Mittel – E2E-Tests benötigen laufende Infrastruktur (Ollama, SearXNG, Tor)
