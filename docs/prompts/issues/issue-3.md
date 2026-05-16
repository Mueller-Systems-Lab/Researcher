# Issue Prompt: T-003

## Ziel
SearXNG als lokales Docker-Compose-Backend starten, Port nur an 127.0.0.1 binden, JSON-API aktivieren, Erreichbarkeit testen.

## Kontext
Docker 29.3.1 ist installiert und läuft. SearXNG soll als isolierter Suchdienst betrieben werden. Kein externer Netzwerkzugriff erlaubt (Sicherheitsregel).

## Betroffene Module
- `SearXNG_Gateway`

## Relevante Dateien
- `searxng/settings.yml`
- `searxng/docker-compose.yml`
- `searxng/limiter.toml` (optional)
- `scripts/start-searxng.sh`

## Architekturregeln
- SearXNG MUSS nur an `127.0.0.1:8080` binden (Host-Port-Mapping)
- JSON-API MUSS aktiviert sein (`search.formats: [html, json]` in `settings.yml`)
- `plugins:` statt `enabled_plugins:` verwenden
- Rate-Limits für lokale IPs nur dann konfigurieren, wenn Valkey vorhanden ist; sonst `server.limiter: false`
- Suchmaschinen nach Bedarf auswählen (minimal: DuckDuckGo, Wikipedia, Wikidata)

## Best Practices
- `SEARXNG_BASE_URL=http://localhost:8080/` setzen
- SearXNG-Konfiguration via Volume-Mount persistieren
- API-Test mit `curl` vor Integration in GPT Researcher

## Akzeptanzkriterien
- **GIVEN** Docker läuft **WHEN** `docker compose -f searxng/docker-compose.yml up -d` ausgeführt wird **THEN** ist SearXNG unter `http://localhost:8080` erreichbar.
- **GIVEN** SearXNG läuft **WHEN** `curl "http://localhost:8080/search?q=test&format=json"` ausgeführt wird **THEN** wird valides JSON zurückgegeben.

## Tests
- `docker ps | grep searxng` (Container läuft)
- `curl -s "http://localhost:8080/search?q=test&format=json" | jq .` (JSON-Response)
- `curl -s "http://<externe-IP>:8080/"` (sollte fehlschlagen – nur localhost)
- `curl -s "http://localhost:8080/search?q=test&format=json" | jq '.results | length'` (Ergebnisse vorhanden)

## Risiken
- 🟢 Niedrig – SearXNG ist ein etablierter Docker-Container
