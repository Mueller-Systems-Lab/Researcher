#!/bin/bash
# ============================================================================
# start-dashboard.sh — Startet GPU/VRAM Live-Dashboard
# ============================================================================
# Nutzung:
#   ./scripts/start-dashboard.sh              # Port 8888 (default)
#   ./scripts/start-dashboard.sh --port 8080  # Anderer Port
#   ./scripts/start-dashboard.sh --check      # Prüft nur GPU-Verfügbarkeit
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8888

check_gpu() {
    if command -v nvidia-smi &>/dev/null; then
        echo "  ✅ nvidia-smi verfügbar"
        nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -1
    else
        echo "  ❌ nvidia-smi nicht gefunden — keine NVIDIA-GPU?"
        echo "  Dashboard zeigt Fehlerstatus an, startet trotzdem."
    fi
}

case "${1:-}" in
    --check|-c)
        check_gpu
        exit 0
        ;;
    --port|-p)
        PORT="${2:-8888}"
        ;;
    --help|-h)
        echo "start-dashboard.sh — GPU/VRAM Live-Dashboard"
        echo ""
        echo "  ./scripts/start-dashboard.sh              Port 8888"
        echo "  ./scripts/start-dashboard.sh --port 8080  Port 8080"
        echo "  ./scripts/start-dashboard.sh --check      Nur GPU-Prüfung"
        exit 0
        ;;
esac

echo "=== GPU/VRAM Live-Dashboard ==="
echo ""
check_gpu
echo ""
DASHBOARD_PORT="$PORT" python -m dashboard.server
