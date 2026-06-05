# =============================================================================
# Live LLM Smoke-Test: Echter Endpoint → Generation → Endmarker (Option 2)
# =============================================================================
# Testet den kritischen Pfad gegen einen echten LM-Studio-Endpoint:
#   Allowlist → Endpoint-Check → Model-Präsenz → Generierung → Endmarker
#
# run_live_llm_check() und Skip-Logik sind in cli/llm_smoke.py ausgelagert
# (Phase B: CLI-Wrapper). Dieses Testmodul importiert sie von dort.
#
# Opt-in via Env (sonst skipped, nicht fail):
#   LM_STUDIO_LIVE_TEST=1
#   LOCAL_LLM_ENDPOINT=http://192.168.43.52:1234
#   LOCAL_LLM_MODEL=qwen2.5-3b-instruct
#
# Ausführung:
#   LM_STUDIO_LIVE_TEST=1 \
#   LOCAL_LLM_ENDPOINT=http://192.168.43.52:1234 \
#   LOCAL_LLM_MODEL=qwen2.5-3b-instruct \
#   pytest -m live -v
# =============================================================================
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cli.llm_smoke import (  # noqa: E402
    _get_endpoint,
    _get_latency_threshold_ms,
    _get_model,
    _is_live_opt_in,
    _live_skip_reason,
    run_live_llm_check,
)

# ═══════════════════════════════════════════════════════════════════════════
# Live Smoke-Test
# ═══════════════════════════════════════════════════════════════════════════

_skip_reason = _live_skip_reason()


@pytest.mark.live
@pytest.mark.smoke
@pytest.mark.skipif(
    _skip_reason is not None, reason=_skip_reason or "live test skipped"
)
def test_live_llm_endpoint_to_endmarker():
    """Kompletter Live-Pfad: Allowlist → Endpoint → Model → Generation → Endmarker.

    Assertions (5):
      1. Endpoint ist per Guard erlaubt
      2. Modell ist präsent
      3. Generierung liefert nicht-leeren Output
      4. Antwort enthält fachliche Keywords (evidence, quellen/sources, belege/daten)
      5. Letzte Zeile ist exakt: 'ist das LLM bereit?'
    """
    endpoint = _get_endpoint()
    model = _get_model()

    result = run_live_llm_check(endpoint, model)

    # Assertion 1: Endpoint ist per Guard erlaubt
    assert result["endpoint_allowed"], (
        f"Endpoint {endpoint} not allowed by guard. "
        "Set LOCAL_LLM_ALLOWED_HOSTS or ALLOW_PRIVATE_LAN_LLM=true"
    )

    # Assertion 2: Modell ist präsent
    assert result["model_present"], (
        f"Model '{model}' not found at {endpoint}/v1/models. "
        f"Error: {result['model_present_error']}"
    )

    # Assertion 3: Generierung liefert nicht-leeren Output
    assert result["generation_ok"], (
        f"Generation failed or produced invalid output. "
        f"Error: {result['generation_error']}"
    )
    assert result["generation_output"].strip(), "Generation output is empty"

    # Assertion 4: Fachliche Keywords
    kw = result["keyword_checks"]
    assert kw.get("evidence"), (
        f"Output missing keyword 'evidence'. "
        f"Got: {result['generation_output'][:200]}..."
    )
    assert kw.get("sources_or_quellen"), (
        f"Output missing source-related keyword (quellen/sources). "
        f"Got: {result['generation_output'][:200]}..."
    )
    assert kw.get("belege_or_daten"), (
        f"Output missing evidence-related keyword (belege/daten/data/facts). "
        f"Got: {result['generation_output'][:200]}..."
    )

    # Assertion 5: Endmarker
    assert result["endmarker_match"], (
        f"Last line is not 'ist das LLM bereit?'. "
        f"Last line: '{result['generation_output'].strip().splitlines()[-1].strip() if result['generation_output'].strip().splitlines() else '(empty)'}'"
    )


@pytest.mark.live
@pytest.mark.smoke
@pytest.mark.skipif(
    _skip_reason is not None, reason=_skip_reason or "live test skipped"
)
def test_live_llm_latency_acceptable():
    """Stellt sicher, dass die Latenz im akzeptablen Bereich liegt.

    Schwellenwert via LOCAL_LLM_LATENCY_THRESHOLD_MS konfigurierbar (default: 30000ms).
    """
    endpoint = _get_endpoint()
    model = _get_model()
    threshold = _get_latency_threshold_ms()

    result = run_live_llm_check(endpoint, model)

    assert result["latency_ms"] > 0, "Latency should be > 0 ms"
    assert result["latency_ms"] < threshold, (
        f"Generation took {result['latency_ms']:.0f}ms (> {threshold}ms threshold)"
    )


# ── Unit-Test: Skip-Logik (läuft immer, braucht keinen Endpoint) ──────────


def test_live_skip_without_env():
    """Ohne LM_STUDIO_LIVE_TEST wird der Test geskipped."""
    # Direkter Test der Skip-Funktion
    skip = _live_skip_reason()
    # In CI/ohne Env sollte skip nicht None sein
    # (nur None wenn alle drei Env-Vars gesetzt sind)
    if not _is_live_opt_in():
        assert skip is not None
        assert "LM_STUDIO_LIVE_TEST" in (skip or "")
