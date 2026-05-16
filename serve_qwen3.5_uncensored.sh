#!/bin/bash
# Serve Qwen3.5-9B-Uncensored-HauhauCS-Aggressive via llama.cpp
# Port: 8086 (gemma4 uses 8085)
# Beide Modelle parallel für Recherche/Learning nutzbar

MODEL_PATH="/home/xxammaxx/Schreibtisch/Researcher/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
BUILD_DIR="/home/xxammaxx/Schreibtisch/gemma4/llama.cpp/build/bin"
SERVER_PATH="$BUILD_DIR/llama-server"

# Ensure shared libraries are found
export LD_LIBRARY_PATH="$BUILD_DIR:$LD_LIBRARY_PATH"

# Parameters optimized for GTX 1070 and Qwen3.5-9B:
# --n-gpu-layers 999: Offload all layers to 8GB VRAM
# -np 1: Single sequence to save VRAM
# --threads 8: Match physical core count of Ryzen 7 5700G
# -c 4096: Context window (wie im Modelfile spezifiziert)
# --flash-attn on: Qwen3.5 unterstützt Flash Attention auf Pascal
# --no-jinja --chat-template chatml: HauhauCS GGUF hat defektes Template
#              in den Metadaten → manuell ChatML setzen
$SERVER_PATH \
  -m "$MODEL_PATH" \
  --n-gpu-layers 999 \
  -np 1 \
  --threads 8 \
  -c 4096 \
  --flash-attn on \
  --mlock \
  --no-jinja \
  --chat-template chatml \
  --alias qwen3.5-uncensored \
  --port 8086 \
  "$@"
