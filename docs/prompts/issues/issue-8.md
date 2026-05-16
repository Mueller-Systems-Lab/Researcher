# Issue Prompt: T-008

## Ziel
nomic-embed-text in Ollama pullen, ChromaDB-Persistenz konfigurieren, `.env`-Variablen setzen (`EMBEDDING_PROVIDER=ollama`, `CHROMA_PERSIST_DIRECTORY=./chroma_db`, etc.), Embedding speichern und abrufen testen.

## Kontext
GPT Researcher nutzt ChromaDB zur Wissensspeicherung. Embeddings werden von nomic-embed-text (137M Parameter) auf der CPU berechnet – die GPU bleibt exklusiv für das LLM reserviert.

## Betroffene Module
- `Vector_Store`, `Embedding_Service`

## Relevante Dateien
- `.env` (GPT Researcher Konfiguration)
- `chroma_db/` (Verzeichnis, bei erstem Lauf automatisch erstellt)

## Architekturregeln
- `EMBEDDING_PROVIDER=ollama`
- `OLLAMA_EMBEDDING_MODEL=nomic-embed-text:latest`
- `CHROMA_PERSIST_DIRECTORY=./chroma_db`
- `CHROMA_COLLECTION=gpt_researcher`
- `EMBEDDING_BATCH_SIZE=8` (CPU-Entlastung)
- Embeddings MÜSSEN auf CPU berechnet werden (GPU exklusiv für LLM)

## Best Practices
- `ollama pull nomic-embed-text:latest` vor erstem Start
- ChromaDB-Persistenz prüfen: nach Recherche müssen Dateien in `chroma_db/` existieren
- Batch-Size klein halten (8) um CPU-Spitzen zu vermeiden
- ChromaDB speichert automatisch bei GPT Researcher Deep-Research-Iterationen

## Akzeptanzkriterien
- **GIVEN** Ollama läuft **WHEN** `ollama pull nomic-embed-text` ausgeführt wird **THEN** ist das Embedding-Modell verfügbar.
- **GIVEN** ChromaDB ist konfiguriert **WHEN** eine Recherche abgeschlossen ist **THEN** sind Embeddings in `chroma_db/` auf Disk persistiert.
- **GIVEN** eine frühere Recherche-Session hat Embeddings gespeichert **WHEN** eine neue Recherche zu einem verwandten Thema gestartet wird **THEN** werden relevante Embeddings aus ChromaDB abgerufen.

## Tests
- `ollama list | grep nomic-embed-text`
- Nach Recherche: `ls chroma_db/` → Dateien vorhanden
- Test-Embedding speichern und per Ähnlichkeitssuche abrufen
- `nvidia-smi` prüfen: Embedding-Berechnung erhöht VRAM nicht signifikant

## Risiken
- 🟢 Niedrig – nomic-embed-text ist ein etabliertes, kleines Modell
