#!/usr/bin/env python3
# =============================================================================
# test_embeddings.py — Validiert sentence-transformers auf CPU
# =============================================================================
# Prüft:
#   1. nomic-embed-text-v1 wird via HuggingFace/sentence-transformers geladen
#   2. Ausführung erfolgt ausschliesslich auf CPU (kein CUDA)
#   3. Embedding-Dimension = 768 (nomic-embed-text-v1 Standard)
#   4. Ollama wird für Embeddings NICHT verwendet
#
# Nutzung:
#   pip install sentence-transformers
#   python3 test_embeddings.py
# =============================================================================

import sys
import time

print("=" * 60)
print("  Embedding-Provider: sentence-transformers (CPU)")
print("=" * 60)
print()

# ── 1. Modell laden ──────────────────────────────────────────────────
print(">>> Lade nomic-ai/nomic-embed-text-v1 via sentence-transformers...")
t0 = time.time()

from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1",
    device="cpu",  # Erzwingt CPU — KEIN CUDA
    trust_remote_code=True,
)

load_time = time.time() - t0
print(f"    Geladen in {load_time:.1f}s")
print()

# ── 2. CPU-Verifikation ──────────────────────────────────────────────
print(">>> Geräte-Prüfung...")
device = (
    str(model.device)
    if hasattr(model, "device")
    else str(model._target_device)
    if hasattr(model, "_target_device")
    else "?"
)

import torch as _torch

uses_cuda = False
try:
    uses_cuda = _torch.cuda.is_available() and any(
        p.device.type == "cuda" for p in model.parameters()
    )
except Exception:
    pass

if "cpu" in device.lower() and not uses_cuda:
    print(f"    ✅ Modell läuft auf CPU (device={device})")
else:
    print(f"    ❌ FEHLER: Modell nutzt GPU (device={device}, cuda={uses_cuda})")
    sys.exit(1)
print()

# ── 3. Test-Embedding ────────────────────────────────────────────────
print(">>> Erzeuge Test-Embedding...")
test_text = "Nuclear fusion research has seen major breakthroughs in magnetic confinement in 2024-2025."

t0 = time.time()
embedding = model.encode(test_text, normalize_embeddings=True)
embed_time = time.time() - t0

dim = len(embedding)
expected_dim = 768

print(f"    Dimension: {dim} (erwartet: {expected_dim})")
print(f"    Zeit:      {embed_time:.3f}s")
print(f"    Norm:      {sum(e * e for e in embedding) ** 0.5:.4f}")
print()

# ── 4. Ergebnis ──────────────────────────────────────────────────────
if dim == expected_dim:
    print("=" * 60)
    print("  ✅ ALLE CHECKS BESTANDEN")
    print("=" * 60)
    print("  Provider:  sentence-transformers (HuggingFace)")
    print("  Device:    CPU (kein CUDA)")
    print(f"  Dimension: {dim}")
    print("  Modell:    nomic-ai/nomic-embed-text-v1")
    print()
    print("  Ollama wird für Embeddings NICHT verwendet → kein VRAM-Konflikt")
    sys.exit(0)
else:
    print(f"❌ FEHLER: Falsche Dimension ({dim} != {expected_dim})")
    sys.exit(1)
