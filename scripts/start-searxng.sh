#!/bin/bash
# Startet SearXNG-Docker-Container für Researcher
# Nutzt docker-compose.yml im searxng/-Verzeichnis
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/searxng/docker-compose.yml"

echo "=== Starte SearXNG ==="
echo "Compose-Datei: $COMPOSE_FILE"

docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "  SearXNG läuft auf http://127.0.0.1:8080"
echo ""
echo "  Test:"
echo "    curl 'http://127.0.0.1:8080/search?q=test&format=json'"
echo ""
