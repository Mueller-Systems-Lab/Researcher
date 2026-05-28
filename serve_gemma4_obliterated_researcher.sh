#!/bin/bash
# ============================================================================
# serve_gemma4_obliterated_researcher.sh
# Startet Gemma 4 E4B OBLITERATED (uncensored) via llama-server für Researcher
# ============================================================================
# GTX 1070 Pascal-sichere Flags:
#   -ctk f32 -ctv f32  → FP32 KV-Cache (verhindert Precision Trap)
#   --flash-attn off    → Pascal hat keine Tensor Cores
#   --n-gpu-layers 999  → Alle 42 Layers auf GPU
#   -np 1               → Single Sequence (VRAM sparen)
#   --threads 8         → Ryzen 7 5700G physische Kerne
#   --reasoning off     → Gemma-4-Thinking deaktivieren (sonst reasoning_content statt content)
#   + API: chat_template_kwargs={"enable_thinking":false} als Fallback
# ============================================================================

MODEL_PATH="/home/xxammaxx/Schreibtisch/gemma4/llama.cpp/models/gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf"
BUILD_DIR="/home/xxammaxx/Schreibtisch/gemma4/llama.cpp/build/bin"
SERVER_PATH="$BUILD_DIR/llama-server"

export LD_LIBRARY_PATH="$BUILD_DIR:$LD_LIBRARY_PATH"

echo "=== Gemma 4 OBLITERATED (Uncensored) for Researcher ==="
echo "Model: $(basename "$MODEL_PATH")"
echo "Port:  8081"
echo "VRAM:  ~3.8 GB used, ~2.1 GB free"
echo ""

exec $SERVER_PATH \
  -m "$MODEL_PATH" \
  --n-gpu-layers 999 \
  -np 1 \
  --threads 8 \
  -ctk f32 \
  -ctv f32 \
  --flash-attn off \
  --jinja \
  --alias gemma4-obliterated \
  --host 127.0.0.1 \
  --port 8081 \
  -c 8192 \
  --reasoning off \
  "$@"
