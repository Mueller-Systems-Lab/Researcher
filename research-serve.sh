#!/bin/bash
# ============================================================
# research-serve.sh — Modell-Server-Menü für Recherche/Learning
# ------------------------------------------------------------
# Verfügbares Modell (nur 8 GB VRAM):
#   Qwen3.5-9B HauhauCS Uncensored → Port 8082
# ============================================================

QWEN_SCRIPT="/home/xxammaxx/Schreibtisch/Researcher/serve_qwen3.5_uncensored.sh"

# Log-Datei
QWEN_LOG="/tmp/qwen3.5_server.log"

# PID
QWEN_PID=""

get_pid() {
    local port=$1
    lsof -ti :"$port" 2>/dev/null || echo ""
}

stop_server() {
    local port=$1
    local name=$2
    local pid=$(get_pid "$port")
    if [ -n "$pid" ]; then
        echo "  → Stoppe $name (PID $pid) auf Port $port..."
        kill "$pid" 2>/dev/null
        sleep 2
        if [ -n "$(get_pid "$port")" ]; then
            kill -9 "$pid" 2>/dev/null
            sleep 1
        fi
        echo "  ✓ $name gestoppt"
    else
        echo "  - $name läuft nicht"
    fi
}


start_qwen() {
    echo ""
    echo "=== Starte Qwen3.5 HauhauCS Uncensored (Port 8082) ==="
    echo ""

    # Prüfen ob Qwen schon läuft
    local qwen_pid=$(get_pid 8082)
    if [ -n "$qwen_pid" ]; then
        echo "  ✓ Qwen läuft bereits (PID $qwen_pid)"
        return
    fi

    # Starten
    echo "  → Starte Qwen3.5-9B HauhauCS..."
    nohup bash "$QWEN_SCRIPT" > "$QWEN_LOG" 2>&1 &
    local pid=$!
    echo "  ✓ PID: $pid"
    echo "  ✓ Log: $QWEN_LOG"

    # Auf Start warten
    echo -n "  → Warte auf Server..."
    for i in $(seq 1 120); do
        sleep 2
        if curl -s -o /dev/null http://127.0.0.1:8082/v1/models 2>/dev/null; then
            echo " BEREIT!"
            echo ""
            echo "  🌐 http://127.0.0.1:8082"
            echo "  🏷  Model: qwen3.5-uncensored"
            echo "  💾 VRAM: ~9B Q4_K_M (~5.3 GB)"
            return
        fi
        echo -n "."
    done
    echo " FEHLER!"
    tail -5 "$QWEN_LOG"
}

status() {
    echo ""
    echo "=== Server-Status ==="
    echo ""

    local qwen_pid=$(get_pid 8082)

    if [ -n "$qwen_pid" ]; then
        echo "  ✅ Qwen3.5 HauhauCS     → Port 8082 (PID $qwen_pid)"
    else
        echo "  ❌ Qwen3.5 HauhauCS     → Port 8082 (gestoppt)"
    fi

    echo ""
    echo "  VRAM gesamt: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null || echo 'nvidia-smi nicht verfügbar')"
    echo ""
}

stop_all() {
    echo ""
    echo "=== Stoppe alle Server ==="
    echo ""
    stop_server 8082 "Qwen3.5"
    echo ""
    echo "  ✓ Alle Server gestoppt"
}

# ---- Main ----
case "${1:-help}" in
    start|qwen|qwen3.5)
        start_qwen
        ;;
    stop)
        stop_all
        ;;
    status)
        status
        ;;
    restart)
        stop_server 8082 "Qwen3.5"
        start_qwen
        ;;
    *)
        echo ""
        echo "research-serve.sh — Modell-Server-Manager"
        echo ""
        echo "Verwendung:"
        echo "  ./research-serve.sh start        Starte Qwen3.5 (Port 8082)"
        echo "  ./research-serve.sh qwen         Starte Qwen3.5 (Alias)"
        echo "  ./research-serve.sh status       Zeige aktuellen Status"
        echo "  ./research-serve.sh stop         Stoppe den Server"
        echo "  ./research-serve.sh restart      Neustart"
        echo ""
        echo "Test:"
        echo "  curl http://127.0.0.1:8082/v1/chat/completions ..."
        echo ""
        ;;
esac
