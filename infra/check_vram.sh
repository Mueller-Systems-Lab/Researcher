#!/usr/bin/env bash
# =============================================================================
# check_vram.sh — VRAM-Diagnose für den Research-Stack
# =============================================================================
# Prüft:
#   - NVIDIA GPU vorhanden?
#   - VRAM-Nutzung (llama.cpp/Ollama Prozess)
#   - Geladene Ollama-Modelle (GPU vs CPU Split)
#   - qwen35-uncensored zu 100% auf GPU?
#   - VRAM-Puffer > 1 GB?
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════"
echo "  VRAM DIAGNOSE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── GPU-Info ──────────────────────────────────────────────────────────
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}❌ nvidia-smi nicht gefunden — keine NVIDIA GPU${NC}"
    exit 1
fi

GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "?")
GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null || echo "?")
MEM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null || echo "?")
MEM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null || echo "?")

echo "  GPU:      ${GPU_NAME}"
echo "  VRAM:     ${MEM_USED} / ${MEM_TOTAL} MiB"
echo "  Auslast.: ${GPU_UTIL}%"
echo ""

# ── Ollama-Prozess ────────────────────────────────────────────────────
OLLAMA_MEM=$(nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader 2>/dev/null | grep -i ollama | awk -F',' '{print $3}' | tr -d ' ' || echo "0")
OLLAMA_MEM=${OLLAMA_MEM:-0}

echo "  Ollama VRAM: ${OLLAMA_MEM} MiB"
echo ""

# ── Ollama PS (Modell-Detail) ─────────────────────────────────────────
if curl -s http://localhost:11434/api/ps 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])
if not models:
    print('  ⚠️  Keine Modelle in Ollama geladen (ollama ps leer)')
    sys.exit(0)

for m in models:
    name = m.get('name', '?')
    size = m.get('size', 0)
    vram = m.get('size_vram', 0)
    size_gb = size / 1e9
    vram_gb = vram / 1e9
    cpu_gb = (size - vram) / 1e9 if size > vram else 0
    pct_gpu = (vram / size * 100) if size > 0 else 0
    print(f'  Modell:   {name}')
    print(f'  Grösse:   {size_gb:.1f} GB total')
    print(f'  GPU:      {vram_gb:.1f} GB ({pct_gpu:.0f}%)')
    print(f'  CPU:      {cpu_gb:.1f} GB')
    print()
" 2>/dev/null; then :; else
    echo "  ⚠️  Ollama nicht erreichbar"
fi

# ── VRAM-Budget-Prüfung ───────────────────────────────────────────────
MEM_FREE=$((MEM_TOTAL - MEM_USED))
echo "  Freier VRAM: ${MEM_FREE} MiB"

if [ "${MEM_USED}" -gt 7000 ]; then
    echo -e "  ${RED}⚠️  WARNUNG: VRAM > 7 GB — Puffer unter 1 GB${NC}"
elif [ "${MEM_USED}" -gt 6000 ]; then
    echo -e "  ${YELLOW}⚠️  VRAM > 6 GB — Puffer unter 2 GB${NC}"
else
    echo -e "  ${GREEN}✅ VRAM im grünen Bereich${NC}"
fi

echo ""

# ── qwen35 GPU-Check ──────────────────────────────────────────────────
if curl -s http://localhost:11434/api/ps 2>/dev/null | python3 -c "
import sys, json
models = json.load(sys.stdin).get('models', [])
for m in models:
    if 'qwen35' in m.get('name', ''):
        vram = m.get('size_vram', 0)
        total = m.get('size', 1)
        pct = vram / total * 100 if total > 0 else 0
        if pct >= 99:
            print('\033[32m  ✅ qwen35-uncensored: 100% GPU\033[0m')
        else:
            print(f'\033[33m  ⚠️  qwen35-uncensored: {pct:.0f}% GPU\033[0m')
        sys.exit(0)
print('\033[31m  ❌ qwen35-uncensored NICHT geladen\033[0m')
" 2>/dev/null; then :; fi

echo ""
echo "═══════════════════════════════════════════════════════"
