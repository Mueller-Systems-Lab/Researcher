#!/usr/bin/env bash
# =============================================================================
# download_model.sh — Lädt Qwen3.5-9B-Uncensored GGUF von HuggingFace
# =============================================================================
# Nutzung:
#   chmod +x download_model.sh
#   ./download_model.sh
#
# Lädt das GGUF nach ~/models/qwen35-uncensored/
# Prüft Dateigrösse nach Download (erwartet: ~5.600.000.000 Bytes)
# =============================================================================
set -euo pipefail

MODEL_DIR="${HOME}/models/qwen35-uncensored"
GGUF_FILE="Qwen3.5-9B-Uncensored-Q4_K_M.gguf"
HF_REPO="LEONW24/Qwen3.5-9B-Uncensored"
EXPECTED_SIZE_MIN=5400000000   # ~5.4 GB minimum

# ── Python/HuggingFace-Check ──────────────────────────────────────────
if ! python3 -c "import huggingface_hub" 2>/dev/null; then
    echo ">>> Installiere huggingface_hub..."
    pip install --break-system-packages huggingface_hub
fi

# ── Zielverzeichnis ────────────────────────────────────────────────────
mkdir -p "${MODEL_DIR}"
cd "${MODEL_DIR}"

# ── Download ───────────────────────────────────────────────────────────
echo ">>> Lade ${GGUF_FILE} von ${HF_REPO}..."
python3 -c "
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id='${HF_REPO}',
    filename='${GGUF_FILE}',
    local_dir='.',
    local_dir_use_symlinks=False,
    resume_download=True,
)
print(f'Download abgeschlossen: {path}')
"

# ── Grössenprüfung ─────────────────────────────────────────────────────
ACTUAL_SIZE=$(stat --format=%s "${GGUF_FILE}" 2>/dev/null || echo 0)
ACTUAL_SIZE_GB=$(echo "scale=2; ${ACTUAL_SIZE} / 1073741824" | bc 2>/dev/null || echo "?")

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Download abgeschlossen"
echo "  Datei:     ${GGUF_FILE}"
echo "  Grösse:    ${ACTUAL_SIZE} Bytes (${ACTUAL_SIZE_GB} GB)"
echo "  Pfad:      ${MODEL_DIR}/${GGUF_FILE}"
echo "═══════════════════════════════════════════════════════"

if [ "${ACTUAL_SIZE}" -lt "${EXPECTED_SIZE_MIN}" ]; then
    echo "❌ FEHLER: Datei zu klein (${ACTUAL_SIZE} < ${EXPECTED_SIZE_MIN} erwartet)"
    exit 1
fi

echo "✅ Grössenprüfung bestanden"
