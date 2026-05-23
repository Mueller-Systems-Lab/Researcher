#!/usr/bin/env bash
# =============================================================================
# pin_llm.sh — Lädt das LLM dauerhaft in den VRAM (keep_alive=-1)
# =============================================================================
# Muss nach jedem Ollama-Neustart ODER nach manuellem ollama stop
# ausgeführt werden.
#
# Nutzung:
#   chmod +x pin_llm.sh
#   ./pin_llm.sh
# =============================================================================
set -euo pipefail

MODEL="qwen35-uncensored:latest"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
MAX_RETRIES=30
RETRY_DELAY=2

echo ">>> Warte auf Ollama (${OLLAMA_URL})..."

# ── Health-Check-Loop ──────────────────────────────────────────────────
for i in $(seq 1 ${MAX_RETRIES}); do
    if curl -s "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama erreichbar nach ${i}s"
        break
    fi
    if [ "$i" -eq "${MAX_RETRIES}" ]; then
        echo "❌ Ollama nicht erreichbar nach $((MAX_RETRIES * RETRY_DELAY))s"
        exit 1
    fi
    sleep ${RETRY_DELAY}
done

# ── Prüfen ob Modell existiert ─────────────────────────────────────────
if ! curl -s "${OLLAMA_URL}/api/tags" | python3 -c "
import sys, json
models = [m['name'] for m in json.load(sys.stdin)['models']]
target = '${MODEL}'.replace(':latest','')
sys.exit(0 if any(target in m for m in models) else 1)
" 2>/dev/null; then
    echo "❌ Modell '${MODEL}' nicht in Ollama registriert"
    echo "   Bitte zuerst: ollama create qwen35-uncensored -f Modelfile"
    exit 1
fi

# ── Modell mit keep_alive=-1 vorladen (bleibt bis manuellem stop) ─────
echo ">>> Lade ${MODEL} mit keep_alive=-1 in VRAM..."
curl -s "${OLLAMA_URL}/api/generate" \
    -d "{\"model\": \"${MODEL}\", \"prompt\": \"ping\", \"stream\": false, \"keep_alive\": -1}" \
    > /dev/null 2>&1

sleep 2

# ── Verifikation ───────────────────────────────────────────────────────
echo ""
if curl -s "${OLLAMA_URL}/api/ps" | python3 -c "
import sys, json
models = json.load(sys.stdin).get('models', [])
found = any('qwen35' in m.get('name','').lower() for m in models)
print('✅ LLM im VRAM gepinnt' if found else '❌ LLM NICHT geladen')
sys.exit(0 if found else 1)
" 2>/dev/null; then
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  qwen35-uncensored ist jetzt dauerhaft im VRAM"
    echo "  Embeddings laufen separat via sentence-transformers (CPU)"
    echo "  Kein VRAM-Konflikt mehr ✅"
    echo "═══════════════════════════════════════════════════════"
else
    echo "❌ Fehler: LLM wurde nicht geladen"
    exit 1
fi
