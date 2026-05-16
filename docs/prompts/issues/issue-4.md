# Issue Prompt: T-004

## Ziel
GPT Researcher klonen/forken, `.env` konfigurieren (LLM, SearXNG, Embeddings), `config/config.py` anpassen, Basisfunktionalität der Web-UI testen.

## Kontext
GPT Researcher (`assafelovic/gpt-researcher`) ist das Orchestrator-Framework. Es muss so konfiguriert werden, dass es das lokale Ollama-LLM und SearXNG verwendet – keine OpenAI-API.

## Betroffene Module
- `Orchestrator`

## Relevante Dateien
- `.env` (GPT Researcher Konfiguration)
- `config/config.py` (Python-Konfiguration)
- `gpt_researcher/` (geklontes Repository)

## Architekturregeln
- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `LLM_MODEL=qwen3-8b-uncensored:latest`
- `RETRIEVER=searx` (vorerst, bis CompositeRetriever in T-007 implementiert ist)
- `SEARX_URL=http://localhost:8080`
- `EMBEDDING_PROVIDER=ollama`
- `MAX_CONCURRENT_REQUESTS=1` (VRAM-Limit)

## Best Practices
- `.env` NIE committen (siehe T-001 .gitignore)
- `config/config.py` als Fallback für Default-Werte nutzen
- GPT Researcher am besten als Git-Submodul oder Fork einbinden
- Web-UI mit `--stream` Flag für Debug-Output starten

## Akzeptanzkriterien
- **GIVEN** GPT Researcher ist geklont **WHEN** `python -m gpt_researcher` ausgeführt wird **THEN** startet die Web-UI unter `http://localhost:8000`.
- **GIVEN** die `.env` ist konfiguriert **WHEN** eine Test-Recherche ausgeführt wird **THEN** wird das lokale LLM verwendet (kein OpenAI-API-Key nötig).

## Tests
- `python -m gpt_researcher --help` (CLI funktioniert)
- Web-UI unter `http://localhost:8000` erreichbar
- Test-Recherche: "Was ist Python?" → Report mit Ollama-generiertem Text
- Logs prüfen: keine OpenAI-API-Aufrufe

## Risiken
- 🟡 Mittel – GPT Researcher Version könnte inkompatibel mit aktueller Ollama-API sein
