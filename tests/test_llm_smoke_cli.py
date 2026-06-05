# =============================================================================
# Smoke-Test für den CLI-Wrapper cli/llm_smoke.py (Phase B)
# =============================================================================
# Testet CLI-Einstiegspunkt: --help, Skip-Logik, Exit-Codes, JSON-Output.
# Läuft immer (keine externe Abhängigkeit).
# =============================================================================
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_MODULE = "cli.llm_smoke"


def _run_cli(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run CLI as python -m cli.llm_smoke with optional args and env."""
    cmd = [sys.executable, "-m", CLI_MODULE, *args]
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    # Ensure no accidental live test activation
    merged_env.pop("LM_STUDIO_LIVE_TEST", None)
    merged_env.pop("LOCAL_LLM_ENDPOINT", None)
    merged_env.pop("LOCAL_LLM_MODEL", None)
    if env:
        merged_env.update(env)  # re-apply after cleanup
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=merged_env,
        timeout=10,
    )


# ── --help ─────────────────────────────────────────────────────────────────


def test_cli_help():
    """--help zeigt Usage-Info."""
    result = _run_cli("--help")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "usage:" in result.stdout.lower() or "usage:" in result.stdout


# ── Skip-Logik (ohne Env) ──────────────────────────────────────────────────


def test_cli_skip_no_env():
    """Ohne LM_STUDIO_LIVE_TEST wird geskipped (Exit 0)."""
    result = _run_cli()
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "SKIPPED" in result.stdout
    assert "LM_STUDIO_LIVE_TEST" in result.stdout


def test_cli_skip_no_endpoint():
    """Mit LM_STUDIO_LIVE_TEST=1 aber ohne Endpoint → skipped."""
    result = _run_cli(env={"LM_STUDIO_LIVE_TEST": "1"})
    assert result.returncode == 0
    assert "SKIPPED" in result.stdout
    assert "LOCAL_LLM_ENDPOINT" in result.stdout


def test_cli_skip_no_model():
    """Mit Endpoint aber ohne Modell → skipped."""
    result = _run_cli(
        env={
            "LM_STUDIO_LIVE_TEST": "1",
            "LOCAL_LLM_ENDPOINT": "http://127.0.0.1:1234",
        }
    )
    assert result.returncode == 0
    assert "SKIPPED" in result.stdout
    assert "LOCAL_LLM_MODEL" in result.stdout


# ── JSON-Output (Skip-Modus) ───────────────────────────────────────────────


def test_cli_json_skip():
    """JSON-Output im Skip-Modus liefert status: skipped."""
    result = _run_cli("--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "skipped"
    assert "LM_STUDIO_LIVE_TEST" in data["reason"]


# ── Keywords-Parsing (CLI-Argument) ────────────────────────────────────────


def test_cli_keywords_parse():
    """--keywords Parsing funktioniert (wird bei Skip nicht angewendet, aber validiert)."""
    result = _run_cli(
        "--json",
        "--keywords",
        '{"topic": ["word1", "word2"], "lang": ["deutsch"]}',
    )
    assert result.returncode == 0  # skipped, parse erfolgt erst nach skip-check
    data = json.loads(result.stdout)
    assert data["status"] == "skipped"


def test_cli_keywords_invalid_json():
    """Ungültiges --keywords JSON führt zu Exit 2."""
    result = _run_cli(
        "--keywords",
        "not-valid-json",
        env={
            "LM_STUDIO_LIVE_TEST": "1",
            "LOCAL_LLM_ENDPOINT": "http://127.0.0.1:1234",
            "LOCAL_LLM_MODEL": "qwen2.5-3b-instruct",
        },
    )
    # JSON parse error happens before endpoint check → exit 2
    assert result.returncode == 2
    assert "Invalid JSON" in result.stderr


# ── Latency Threshold (CLI-Argument + Env) ─────────────────────────────────


def test_cli_latency_threshold_help():
    """--help zeigt latency-threshold Option."""
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "--latency-threshold" in result.stdout


# ── Timeout-Argument ───────────────────────────────────────────────────────


def test_cli_timeout_help():
    """--help zeigt timeout Option."""
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "--timeout" in result.stdout


# ── Exit-Code: Cloud-Endpoint (simuliert via falschem Endpoint) ───────────


@pytest.mark.slow
def test_cli_fail_cloud_endpoint():
    """Cloud-Endpoint wird vom Guard blockiert → Exit 1 (fail)."""
    result = _run_cli(
        "--json",
        "--timeout",
        "3",
        env={
            "LM_STUDIO_LIVE_TEST": "1",
            "LOCAL_LLM_ENDPOINT": "http://api.openai.com/v1",
            "LOCAL_LLM_MODEL": "gpt-4",
        },
    )
    assert result.returncode == 1, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["status"] == "fail"
    assert not data["checks"]["endpoint_allowed"]


# ── Integration: run_live_llm_check() importierbar ──────────────────────────


def test_run_live_llm_check_importable():
    """run_live_llm_check ist aus cli.llm_smoke importierbar."""
    from cli.llm_smoke import run_live_llm_check

    assert callable(run_live_llm_check)


def test_run_live_llm_check_with_keywords():
    """run_live_llm_check akzeptiert keywords-Parameter (Unit-Test via Mock)."""
    from unittest.mock import patch

    from cli.llm_smoke import run_live_llm_check

    # Mock the endpoint check to fail fast (no real HTTP).
    # check_endpoint_local is imported inside run_live_llm_check() from
    # config.local_llm_runtime, so we patch there.
    with patch("config.local_llm_runtime.check_endpoint_local", return_value=False):
        result = run_live_llm_check(
            "http://127.0.0.1:1234",
            "test-model",
            keywords={"topic": ["research"], "lang": ["deutsch"]},
        )
        assert not result["endpoint_allowed"]
        assert result["generation_error"] == "Endpoint not allowed by guard"


def test_get_latency_threshold_ms_default():
    """_get_latency_threshold_ms liefert 30000 als Default."""
    from cli.llm_smoke import _get_latency_threshold_ms

    # Unset env
    old = os.environ.pop("LOCAL_LLM_LATENCY_THRESHOLD_MS", None)
    try:
        assert _get_latency_threshold_ms() == 30000
    finally:
        if old is not None:
            os.environ["LOCAL_LLM_LATENCY_THRESHOLD_MS"] = old


def test_get_latency_threshold_ms_custom():
    """_get_latency_threshold_ms respektiert Env-Variable."""
    from cli.llm_smoke import _get_latency_threshold_ms

    os.environ["LOCAL_LLM_LATENCY_THRESHOLD_MS"] = "5000"
    try:
        assert _get_latency_threshold_ms() == 5000
    finally:
        del os.environ["LOCAL_LLM_LATENCY_THRESHOLD_MS"]
