#!/usr/bin/env python3
# =============================================================================
# integration_test.py — Validiert LLM+Embedding-Stack ohne VRAM-Konflikt
# =============================================================================
# Testet:
#   1. LLM-Request an Ollama (qwen35-uncensored) → korrekte Antwort
#   2. 5 Embeddings via sentence-transformers (CPU) → Vektor-Dim = 768
#   3. VRAM vor/nach Embedding-Calls → Delta = 0 (kein GPU-Memory-Change)
#   4. LLM nach Embedding-Calls → antwortet weiterhin korrekt
#
# Nutzung:
#   pip install sentence-transformers requests
#   python3 integration_test.py
# =============================================================================

import subprocess
import sys
import time


def get_vram_used_mib():
    """Liest VRAM-Nutzung in MiB via nvidia-smi."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        )
        return int(out.strip())
    except Exception:
        return -1


# ── Vorbereitung ────────────────────────────────────────────────────
print("=" * 60)
print("  INTEGRATIONS-TEST: LLM + Embedding (CPU)")
print("=" * 60)
print()

vram_before = get_vram_used_mib()
print(f"VRAM vor Test:  {vram_before} MiB")
print()

# ── Test 1: LLM-Request ─────────────────────────────────────────────
print(">>> Test 1: LLM-Request an qwen35-uncensored...")
import requests

try:
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen35-uncensored:latest",
            "messages": [
                {"role": "user", "content": "Say 'OK' exactly, nothing else."}
            ],
            "stream": False,
        },
        timeout=60,
    )
    llm_response = r.json()["message"]["content"].strip()
    assert "OK" in llm_response.upper(), f"Unerwartete Antwort: {llm_response}"
    print(f'   ✅ LLM antwortet: "{llm_response}"')
except Exception as e:
    print(f"   ❌ LLM-Test fehlgeschlagen: {e}")
    sys.exit(1)
print()

# ── Test 2: Embeddings (CPU) ────────────────────────────────────────
print(">>> Test 2: 5 Embeddings via sentence-transformers (CPU)...")
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1", device="cpu", trust_remote_code=True
)

texts = [
    "Nuclear fusion energy breakthrough 2024",
    "Magnetic confinement fusion reactor advances",
    "Laser inertial fusion energy gain record",
    "Tokamak plasma temperature milestone",
    "Commercial fusion power plant timeline",
]

t0 = time.time()
embeddings = model.encode(texts, normalize_embeddings=True)
embed_time = time.time() - t0

assert len(embeddings) == 5, f"Erwartet 5 Embeddings, bekam {len(embeddings)}"
assert embeddings.shape[1] == 768, f"Erwartet Dim=768, bekam {embeddings.shape[1]}"
print(f"   ✅ {len(embeddings)} Embeddings erzeugt in {embed_time:.2f}s")
print(
    f"      Dimension: {embeddings.shape[1]}, Norm: {sum(e * e for e in embeddings[0]) ** 0.5:.4f}"
)
print()

# ── Test 3: VRAM-Delta ──────────────────────────────────────────────
print(">>> Test 3: VRAM-Delta durch Embeddings...")
vram_after_embed = get_vram_used_mib()
delta = vram_after_embed - vram_before
print(f"   VRAM vorher:  {vram_before} MiB")
print(f"   VRAM nachher: {vram_after_embed} MiB")
print(f"   Delta:        {delta:+d} MiB")
if abs(delta) <= 100:
    print("   ✅ VRAM-Delta ≈ 0 — Embeddings nutzen kein GPU-Memory")
else:
    print(f"   ❌ VRAM-Delta {delta} MiB — Embeddings scheinen GPU zu nutzen!")
    sys.exit(1)
print()

# ── Test 4: LLM nach Embeddings ─────────────────────────────────────
print(">>> Test 4: LLM-Request nach Embedding-Calls...")
try:
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen35-uncensored:latest",
            "messages": [{"role": "user", "content": "Was ist 2+2? Nur die Zahl."}],
            "stream": False,
        },
        timeout=60,
    )
    llm_response2 = r.json()["message"]["content"].strip()
    assert "4" in llm_response2, f"Unerwartete Antwort: {llm_response2}"
    print(f'   ✅ LLM antwortet korrekt: "{llm_response2}"')
except Exception as e:
    print(f"   ❌ LLM nach Embeddings fehlgeschlagen: {e}")
    sys.exit(1)
print()

# ── Ergebnis ────────────────────────────────────────────────────────
vram_final = get_vram_used_mib()
print("=" * 60)
print("  ✅ ALLE 4 TESTS BESTANDEN")
print("=" * 60)
print("  LLM (qwen35-uncensored):    dauerhaft in Ollama/VRAM")
print("  Embeddings (nomic-embed):   sentence-transformers/CPU")
print(f"  VRAM-Delta durch Embeddings: {delta:+d} MiB")
print(f"  VRAM final:                 {vram_final} MiB")
print()
print("  Kein VRAM-Konflikt. LLM + Embeddings koexistieren.")
