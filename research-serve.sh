#!/bin/bash
# ============================================================
# research-serve.sh — Modell-Server-Menü für Recherche/Learning
# ------------------------------------------------------------
# Verfügbare Modelle (nacheinander, da nur 8 GB VRAM):
#   1. Gemma 4 E4B OBLITERATED  (7.5B, Q4_K_M) → Port 8085
#   2. Qwen3.5-9B HauhauCS      (9B,  Q4_K_M) → Port 8086
# ============================================================

GEMMA4_SCRIPT="/home/xxammaxx/Schreibtisch/gemma4/serve_gemma4_obliterated.sh"
QWEN_SCRIPT="/home/xxammaxx/Schreibtisch/Researcher/serve_qwen3.5_uncensored.sh"

# Log-Dateien
GEMMA4_LOG="/tmp/gemma4_server.log"
QWEN_LOG="/tmp/qwen3.5_server.log"

# PIDs
GEMMA4_PID=""
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
        # Force kill if still running
        pid=$(get_pid "$port")
        if [ -n "$pid" ]; then
            kill -9 "$pid" 2>/dev/null
            sleep 1
        fi
        echo "  ✓ $name gestoppt"
    else
        echo "  - $name läuft nicht"
    fi
}

start_gemma4() {
    echo ""
    echo "=== Starte Gemma 4 OBLITERATED (Port 8085) ==="
    echo ""
    
    # Qwen stoppen falls am Laufen
    local qwen_pid=$(get_pid 8086)
    if [ -n "$qwen_pid" ]; then
        echo "  ⚠ Qwen läuft noch auf Port 8086 — wird gestoppt..."
        stop_server 8086 "Qwen3.5"
    fi
    
    # Prüfen ob Gemma schon läuft
    local gemma_pid=$(get_pid 8085)
    if [ -n "$gemma_pid" ]; then
        echo "  ✓ Gemma 4 läuft bereits (PID $gemma_pid)"
        return
    fi
    
    # Starten
    echo "  → Starte Gemma 4 OBLITERATED..."
    nohup bash "$GEMMA4_SCRIPT" > "$GEMMA4_LOG" 2>&1 &
    local pid=$!
    echo "  ✓ PID: $pid"
    echo "  ✓ Log: $GEMMA4_LOG"
    
    # Auf Start warten
    echo -n "  → Warte auf Server..."
    for i in $(seq 1 120); do
        sleep 2
        if curl -s -o /dev/null http://127.0.0.1:8085/v1/models 2>/dev/null; then
            echo " BEREIT!"
            echo ""
            echo "  🌐 http://127.0.0.1:8085"
            echo "  🏷  Model: gemma4-obliterated"
            echo "  💾 VRAM: ~7.5B Q4_K_M (5.0 GB)"
            return
        fi
        echo -n "."
    done
    echo " FEHLER!"
    tail -5 "$GEMMA4_LOG"
}

start_qwen() {
    echo ""
    echo "=== Starte Qwen3.5 HauhauCS Uncensored (Port 8086) ==="
    echo ""
    
    # Gemma stoppen falls am Laufen
    local gemma_pid=$(get_pid 8085)
    if [ -n "$gemma_pid" ]; then
        echo "  ⚠ Gemma 4 läuft noch auf Port 8085 — wird gestoppt..."
        stop_server 8085 "Gemma 4"
    fi
    
    # Prüfen ob Qwen schon läuft
    local qwen_pid=$(get_pid 8086)
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
        if curl -s -o /dev/null http://127.0.0.1:8086/v1/models 2>/dev/null; then
            echo " BEREIT!"
            echo ""
            echo "  🌐 http://127.0.0.1:8086"
            echo "  🏷  Model: qwen3.5-uncensored"
            echo "  💾 VRAM: ~9B Q4_K_M (5.6 GB)"
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
    
    local gemma_pid=$(get_pid 8085)
    local qwen_pid=$(get_pid 8086)
    local gemma_vram=""
    local qwen_vram=""
    
    if [ -n "$gemma_pid" ]; then
        gemma_vram=$(ps -p "$gemma_pid" -o rss= 2>/dev/null)
        echo "  ✅ Gemma 4 OBLITERATED  → Port 8085 (PID $gemma_pid)"
    else
        echo "  ❌ Gemma 4 OBLITERATED  → Port 8085 (gestoppt)"
    fi
    
    if [ -n "$qwen_pid" ]; then
        qwen_vram=$(ps -p "$qwen_pid" -o rss= 2>/dev/null)
        echo "  ✅ Qwen3.5 HauhauCS     → Port 8086 (PID $qwen_pid)"
    else
        echo "  ❌ Qwen3.5 HauhauCS     → Port 8086 (gestoppt)"
    fi
    
    echo ""
    echo "  VRAM gesamt: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null)"
    echo ""
}

stop_all() {
    echo ""
    echo "=== Stoppe alle Server ==="
    echo ""
    stop_server 8085 "Gemma 4"
    stop_server 8086 "Qwen3.5"
    echo ""
    echo "  ✓ Alle Server gestoppt"
}

# ---- Main ----
case "${1:-help}" in
    gemma|gemma4)
        start_gemma4
        ;;
    qwen|qwen3.5)
        start_qwen
        ;;
    stop)
        stop_all
        ;;
    status)
        status
        ;;
    restart-gemma)
        stop_server 8085 "Gemma 4"
        start_gemma4
        ;;
    restart-qwen)
        stop_server 8086 "Qwen3.5"
        start_qwen
        ;;
    *)
        echo ""
        echo "research-serve.sh — Modell-Server-Manager"
        echo ""
        echo "Verwendung:"
        echo "  ./research-serve.sh gemma       Starte Gemma 4 OBLITERATED  (Port 8085)"
        echo "  ./research-serve.sh qwen        Starte Qwen3.5 HauhauCS     (Port 8086)"
        echo "  ./research-serve.sh status      Zeige aktuellen Status"
        echo "  ./research-serve.sh stop        Stoppe alle Server"
        echo "  ./research-serve.sh restart-gemma  Neustart Gemma"
        echo "  ./research-serve.sh restart-qwen   Neustart Qwen"
        echo ""
        echo "Hinweis: Nur EIN Modell gleichzeitig (8 GB VRAM-Limit)"
        echo "         Beim Start wird das andere automatisch gestoppt."
        echo ""
        echo "Test:"
        echo "  curl http://127.0.0.1:8085/v1/chat/completions ...  (Gemma)"
        echo "  curl http://127.0.0.1:8086/v1/chat/completions ...  (Qwen)"
        echo ""
        ;;
esac
