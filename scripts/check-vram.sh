#!/bin/bash
# =============================================================================
# check-vram.sh — VRAM-Monitoring für GTX 1070 (8 GB)
# =============================================================================
# Zeigt die aktuelle VRAM-Auslastung aller GPUs und warnt bei Überlast.
#
# Nutzung:
#   ./scripts/check-vram.sh              # Einmalige Abfrage
#   ./scripts/check-vram.sh --watch      # Dauerhaftes Monitoring (alle 2s)
#   ./scripts/check-vram.sh --json       # Als JSON für Weiterverarbeitung
# =============================================================================

set -euo pipefail

# VRAM-Limit in MiB (7.5 GB = 7680 MiB,留 512 MiB Puffer)
VRAM_LIMIT_MIB=7680
VRAM_TOTAL_MIB=8192
WARNING_THRESHOLD=90  # Prozent

check_vram() {
    if ! command -v nvidia-smi &>/dev/null; then
        echo "❌ nvidia-smi nicht gefunden — keine NVIDIA-GPU?"
        exit 1
    fi

    nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,utilization.memory \
        --format=csv,noheader,nounits 2>/dev/null
}

format_output() {
    local IFS=','
    while read -r idx name used total gpu_util mem_util; do
        used=${used// /}
        total=${total// /}
        pct=$((used * 100 / total))
        status="✅"
        if [ "$pct" -ge "$WARNING_THRESHOLD" ]; then
            status="⚠️"
        fi
        if [ "$used" -ge "$VRAM_LIMIT_MIB" ]; then
            status="🔴"
        fi
        echo "$status GPU $idx ($name): ${used}MiB / ${total}MiB (${pct}%) | GPU-Auslastung: ${gpu_util}% | Speicher-Auslastung: ${mem_util}%"
    done
}

watch_mode() {
    echo "VRAM-Monitoring (alle 2s) — Drücke Ctrl+C zum Beenden"
    echo "Limit: ${VRAM_LIMIT_MIB}MiB / ${VRAM_TOTAL_MIB}MiB (${WARNING_THRESHOLD}%)"
    echo ""
    while true; do
        clear 2>/dev/null || true
        echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
        echo ""
        check_vram | format_output
        echo ""
        echo "--- Prozesse mit GPU-Nutzung ---"
        nvidia-smi --query-compute-apps=pid,process_name,used_memory \
            --format=csv,noheader 2>/dev/null | head -5 || true
        sleep 2
    done
}

json_mode() {
    echo "{"
    echo '  "timestamp": "'$(date -Iseconds)'",'
    echo '  "limit_mib": '$VRAM_LIMIT_MIB','
    echo '  "total_mib": '$VRAM_TOTAL_MIB','
    echo '  "gpus": ['
    local first=true
    while IFS=, read -r idx name used total gpu_util mem_util; do
        if [ "$first" = true ]; then first=false; else echo ","; fi
        used=${used// /}
        total=${total// /}
        pct=$((used * 100 / total))
        echo -n "    {\"index\":$idx,\"name\":\"${name// /}\",\"used_mib\":$used,\"total_mib\":$total,\"pct\":$pct,\"gpu_util\":${gpu_util// /},\"mem_util\":${mem_util// /}}"
    done <<< "$(check_vram)"
    echo ""
    echo '  ]'
    echo "}"
}

# ---- Main ----
case "${1:-}" in
    --watch|-w)
        watch_mode
        ;;
    --json|-j)
        json_mode
        ;;
    --help|-h)
        echo "check-vram.sh — VRAM-Monitoring"
        echo ""
        echo "  ./scripts/check-vram.sh            Einmalige Abfrage"
        echo "  ./scripts/check-vram.sh --watch    Dauerhaftes Monitoring"
        echo "  ./scripts/check-vram.sh --json     Als JSON-Ausgabe"
        echo ""
        ;;
    *)
        check_vram | format_output
        ;;
esac
