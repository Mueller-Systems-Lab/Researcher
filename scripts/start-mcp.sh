#!/bin/bash
# =============================================================================
# start-mcp.sh — Startet den MCP-Tools-Server
# =============================================================================
# Nutzung:
#   ./scripts/start-mcp.sh              # Port 8765 (default)
#   ./scripts/start-mcp.sh --port 9000  # Anderer Port
#   ./scripts/start-mcp.sh --check      # Nur Tools auflisten
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8765

case "${1:-}" in
    --check|-c)
        python3 -c "
from mcp_tools.registry import init_tools, list_tools
init_tools()
for t in list_tools():
    print(f'  ✅ {t}')
print(f'  ({len(list_tools())} Tools registriert)')
"
        exit 0
        ;;
    --port|-p)
        PORT="${2:-8765}"
        ;;
    --help|-h)
        echo "start-mcp.sh — MCP-Tools-Server"
        echo ""
        echo "  ./scripts/start-mcp.sh             Port 8765"
        echo "  ./scripts/start-mcp.sh --port 9000 Port 9000"
        echo "  ./scripts/start-mcp.sh --check     Tools auflisten"
        exit 0
        ;;
esac

echo "=== MCP-Tools-Server ==="
echo ""
python3 -c "
from mcp_tools.registry import init_tools, list_tools
init_tools()
for t in list_tools():
    print(f'  ✅ {t}')
"
echo ""
MCP_PORT="$PORT" python -m mcp_tools.server
