# Issue Prompt: T-006

## Ziel
Whoosh-Schema definieren und Index anlegen, Crawler-Output in Index schreiben, DarknetRetriever-Klasse implementieren (erweitert GPT-Researcher abstrakte Retriever-Klasse), in `gpt_researcher/retrievers/__init__.py` registrieren, synthetische URI-Generierung (`darknet://`).

## Kontext
Der DarknetRetriever ist die Brücke zwischen dem Whoosh-Volltextindex und GPT Researcher. Er implementiert die abstrakte `Retriever`-Klasse und ermöglicht die nahtlose Integration in den Suchprozess.

## Betroffene Module
- `Darknet_Search`

## Relevante Dateien
- `gpt_researcher/retrievers/darknet/darknet.py`
- `gpt_researcher/retrievers/darknet/__init__.py`
- `gpt_researcher/retrievers/__init__.py` (bestehende Datei – DarknetRetriever registrieren)
- `darknet_index/` (Verzeichnis für Whoosh-Index)

## Architekturregeln
- Whoosh-Schema: `url` (ID, unique), `author` (TEXT), `timestamp` (DATETIME), `content` (TEXT)
- DarknetRetriever MUSS die abstrakte `Retriever`-Klasse von GPT Researcher erweitern
- `search()`-Methode MUSS `max_results` respektieren
- Suchergebnisse MÜSSEN synthetische URIs enthalten (`darknet://<forum-id>/post/<id>`)
- `MultifieldParser` für Suche in `content`, `author`, `url`

## Best Practices
- Whoosh-Index bei erstem Start automatisch anlegen (wenn nicht existiert)
- Index regelmäßig optimieren (`ix.optimize()`)
- Content-Snippets auf ~300 Zeichen kürzen für Ergebnisdarstellung
- Fehlerbehandlung: Index nicht vorhanden → leere Ergebnisliste (kein Crash)

## Akzeptanzkriterien
- **GIVEN** der Whoosh-Index ist befüllt **WHEN** nach einem Begriff gesucht wird **THEN** werden relevante Posts mit URL, Autor und Content-Snippet zurückgegeben.
- **GIVEN** ein Suchergebnis existiert **WHEN** es formatiert wird **THEN** enthält es eine synthetische `darknet://`-URI.
- **GIVEN** der DarknetRetriever ist registriert **WHEN** GPT Researcher eine Suche ausführt **THEN** kann der Retriever über die Retriever-Map instanziiert werden.

## Tests
- Whoosh-Index mit Testdaten befüllen und `search()` aufrufen
- `DarknetRetriever.search("test", max_results=5)` → max. 5 Ergebnisse
- URI-Format prüfen: `darknet://forum/post-<id>`
- `isinstance(darknet_retriever, Retriever)` → `True`
- Leerer Index: `search()` → leere Liste (kein Fehler)

## Risiken
- 🟢 Niedrig – Whoosh ist eine ausgereifte Pure-Python-Bibliothek
