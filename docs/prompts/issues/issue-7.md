# Issue Prompt: T-007

## Ziel
CompositeRetriever-Klasse implementieren: parallele Abfrage SearXNG + DarknetRetriever, Deduplizierung anhand URL, Fehlertoleranz (Fallback bei Ausfall eines Backends), in `config.py` registrieren (`RETRIEVER=custom`).

## Kontext
GPT Researcher erwartet genau einen Retriever. Der CompositeRetriever fasst SearXNG und DarknetRetriever unter einer einheitlichen Schnittstelle zusammen und merged die Ergebnisse.

## Betroffene Module
- `Search_Composite`

## Relevante Dateien
- `gpt_researcher/retrievers/custom/custom.py` (CompositeRetriever-Implementierung)
- `gpt_researcher/retrievers/custom/__init__.py`
- `config/config.py` (RETRIEVER=custom Mapping)

## Architekturregeln
- `search()`-Methode MUSS beide Backends PARALLEL abfragen (`asyncio`)
- Ergebnisse MÜSSEN anhand URL dedupliziert werden
- Ergebnisliste auf max. 20 Einträge begrenzen
- Fehlertoleranz: Ein ausgefallenes Backend DARF NICHT zum Gesamtfehler führen
- Bei SearXNG-Ausfall: Warnung loggen, Darknet-Ergebnisse zurückgeben
- Bei leerem Darknet-Index: Nur SearXNG-Ergebnisse zurückgeben
- Interface-Konformität mit GPT Researcher `Retriever`-Klasse

## Best Practices
- `asyncio.gather()` mit `return_exceptions=True` für Fehlertoleranz
- Deduplizierung mit `set()` (URLs als Keys)
- Timeout pro Backend (z.B. 10 Sekunden)
- Logging für Debugging: welche Backends wie viele Ergebnisse lieferten
- `CompositeRetriever` als primären Retriever in `config.py` registrieren

## Akzeptanzkriterien
- **GIVEN** beide Backends sind verfügbar **WHEN** `search(query)` aufgerufen wird **THEN** werden Ergebnisse aus SearXNG und Darknet gemerged.
- **GIVEN** SearXNG ist nicht erreichbar **WHEN** `search(query)` aufgerufen wird **THEN** werden nur Darknet-Ergebnisse zurückgegeben (kein Fehler, Warnung im Log).
- **GIVEN** der Darknet-Index ist leer **WHEN** `search(query)` aufgerufen wird **THEN** werden nur SearXNG-Ergebnisse zurückgegeben.
- **GIVEN** beide Backends liefern dieselbe URL **WHEN** gemerged wird **THEN** erscheint sie nur einmal.

## Tests
- Unit-Test: Mock SearXNG + Mock Darknet → merge+Dedup
- Integrationstest: Echter SearXNG + Mock Darknet (oder umgekehrt)
- Fallback-Test: SearXNG-URL nicht erreichbar → Darknet-Ergebnisse
- Fallback-Test: Darknet-Index leer → SearXNG-Ergebnisse
- Deduplizierungstest: Beide Backends liefern gleiche URL

## Risiken
- 🟡 Mittel – Asynchrone Programmierung (`asyncio`) kann komplex sein
