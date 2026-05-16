#!/bin/bash
# ============================================================================
# start-researcher.sh — Startet GPT Researcher Web-UI
# ============================================================================
# Voraussetzungen:
#   1. Python-Venv aktiviert: source .venv/bin/activate
#   2. .env konfiguriert (siehe .env.example)
#   3. Ollama läuft: ollama serve
#   4. SearXNG läuft: scripts/start-searxng.sh (optional, für Websuche)
#
# Nutzung:
#   ./scripts/start-researcher.sh           # Startet Web-UI
#   ./scripts/start-researcher.sh --check   # Prüft Konfiguration
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
check_warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
check_fail() { echo -e "  ${RED}✗${NC} $1"; }

check_env() {
    echo ""
    echo "=== Konfigurationsprüfung ==="
    echo ""

    # .env vorhanden?
    if [ -f "$SCRIPT_DIR/.env" ]; then
        check_ok ".env vorhanden"
        source "$SCRIPT_DIR/.env"
    else
        check_fail ".env nicht gefunden"
        check_warn "Kopiere .env.example nach .env und passe Werte an"
        return 1
    fi

    # Python-Venv aktiv?
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        check_ok "Python-Venv aktiv: $VIRTUAL_ENV"
    else
        check_warn "Kein Python-Venv aktiv — verwende System-Python"
    fi

    # Ollama läuft?
    if curl -s -o /dev/null "http://${OLLAMA_BASE_URL:-localhost:11434}/api/tags" 2>/dev/null; then
        check_ok "Ollama erreichbar unter ${OLLAMA_BASE_URL:-localhost:11434}"
    else
        check_fail "Ollama nicht erreichbar unter ${OLLAMA_BASE_URL:-localhost:11434}"
        check_warn "Starte: ollama serve"
    fi

    # SearXNG läuft? (nur Warnung, nicht kritisch)
    if curl -s -o /dev/null "${SEARX_URL:-http://localhost:8080}/search?q=test&format=json" 2>/dev/null; then
        check_ok "SearXNG erreichbar unter ${SEARX_URL:-http://localhost:8080}"
    else
        check_warn "SearXNG nicht erreichbar unter ${SEARX_URL:-http://localhost:8080}"
        check_warn "Starte: ./scripts/start-searxng.sh"
    fi

    # GPT Researcher installiert?
    if python -c "import gpt_researcher" 2>/dev/null; then
        check_ok "GPT Researcher (Python-Modul) installiert"
    else
        check_fail "GPT Researcher nicht installiert"
        check_warn "Installiere: pip install -r requirements.txt"
    fi
}

start_ui() {
    echo ""
    echo "=== Starte GPT Researcher Web-UI ==="
    echo ""
    echo "  URL: http://localhost:8000"
    echo "  Drücke Ctrl+C zum Beenden"
    echo ""
    python -m gpt_researcher "$@"
}

# ---- Main ----
case "${1:-}" in
    --check|-c)
        check_env
        ;;
    --help|-h)
        echo ""
        echo "start-researcher.sh — GPT Researcher Web-UI"
        echo ""
        echo "  ./scripts/start-researcher.sh           Startet die Web-UI"
        echo "  ./scripts/start-researcher.sh --check   Prüft die Konfiguration"
        echo "  ./scripts/start-researcher.sh --help    Zeigt diese Hilfe"
        echo ""
        ;;
    *)
        check_env
        start_ui "$@"
        ;;
esac
