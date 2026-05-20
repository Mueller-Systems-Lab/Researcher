"""Security Regression Tests — Netzwerk, Cloud, Hashing, SQL, SSL-Verify.

Alle Tests sind gemockt. Keine echten externen Netzwerkaufrufe.
"""

import hashlib
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# ═══════════════════════════ NETZWERK-TIMEOUTS ════════════════════════════════


def test_runtime_smoke_ollama_uses_timeout():
    """Runtime-Smoke Ollama-Check verwendet Timeout."""
    from scripts.runtime_smoke import check_ollama

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "nomic-embed-text:latest"},
                {"name": "qwen3.5-uncensored-no-thinking:latest"},
            ]
        }
        mock_get.return_value = mock_response
        check_ollama()
        call_kwargs = mock_get.call_args.kwargs
        assert "timeout" in call_kwargs, "Ollama-Check muss Timeout verwenden"


def test_runtime_smoke_searxng_uses_timeout():
    """Runtime-Smoke SearXNG-Check verwendet Timeout."""
    from scripts.runtime_smoke import check_searxng

    with patch("scripts.runtime_smoke.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"title": "t"}]}
        mock_get.return_value = mock_response
        check_searxng()
        call_kwargs = mock_get.call_args.kwargs
        assert "timeout" in call_kwargs, "SearXNG-Check muss Timeout verwenden"


def test_happy_path_searxng_uses_timeout():
    """Happy-Path SearXNG-Call verwendet Timeout."""
    from scripts.research_happy_path import search_searxng

    with patch("scripts.research_happy_path.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"title": "t"}]}
        mock_get.return_value = mock_response
        search_searxng("test")
        call_kwargs = mock_get.call_args.kwargs
        assert "timeout" in call_kwargs, "Happy-Path SearXNG muss Timeout verwenden"


def test_happy_path_ollama_uses_timeout():
    """Happy-Path Ollama-Call verwendet Timeout."""
    from scripts.research_happy_path import summarize_with_ollama

    with patch("scripts.research_happy_path.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "summary"}
        mock_post.return_value = mock_response
        summarize_with_ollama("q", [{"title": "t", "content": "c"}], "model")
        call_kwargs = mock_post.call_args.kwargs
        assert "timeout" in call_kwargs, "Happy-Path Ollama muss Timeout verwenden"


# ═══════════════════════════ CLOUD-BLOCKER ════════════════════════════════════


def test_cloud_blocker_openai_blocked():
    """Cloud-Blocker blockiert OpenAI ohne ALLOW_CLOUD."""
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
        assert check_cloud_blocker() is False


def test_cloud_blocker_tavily_blocked():
    """Cloud-Blocker blockiert Tavily ohne ALLOW_CLOUD."""
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(os.environ, {"RETRIEVER": "tavily"}, clear=True):
        assert check_cloud_blocker() is False


def test_cloud_blocker_anthropic_blocked():
    """Cloud-Blocker blockiert Anthropic ohne ALLOW_CLOUD."""
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}, clear=True):
        assert check_cloud_blocker() is False


def test_cloud_blocker_allowed_with_flag():
    """ALLOW_CLOUD=true → Happy-Path blockiert Cloud im Local-First-Modus."""
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(
        os.environ,
        {"ALLOW_CLOUD": "true", "LLM_PROVIDER": "openai"},
    ):
        # check_cloud_blocker returns False when ALLOW_CLOUD=true
        # (Happy-Path erfordert strikt Local-First)
        assert check_cloud_blocker() is False


def test_cloud_blocker_clean_when_nothing_set():
    """Sauber, wenn keine Cloud-Provider gesetzt."""
    from scripts.research_happy_path import check_cloud_blocker

    with patch.dict(os.environ, {}, clear=True):
        assert check_cloud_blocker() is True


# ═══════════════════════════ HASHING REGRESSION ═══════════════════════════════


def test_own_code_uses_usedforsecurity_for_md5():
    """Sucht nach hashlib.md5( im Projektcode ohne usedforsecurity=False.

    Ausnahmen: Submodul (gpt_researcher/) ist ausgeschlossen.
    """
    import glob

    violations = []
    for fpath in glob.glob("**/*.py", recursive=True):
        # Skip submodule
        if "gpt_researcher/" in fpath:
            continue
        # Skip cache dirs
        if "__pycache__" in fpath or ".venv" in fpath:
            continue
        try:
            with open(fpath) as f:
                content = f.read()
        except Exception:
            continue
        if "hashlib.md5(" in content:
            # Must have usedforsecurity=False
            if "usedforsecurity=False" not in content:
                if "noqa: B324" not in content:
                    violations.append(fpath)

    assert not violations, (
        f"Projektdateien mit hashlib.md5() ohne usedforsecurity=False: {violations}"
    )


def test_hashing_sha256_is_available():
    """SHA-256 ist verfügbar (Grundlage für sicheren Hash)."""
    digest = hashlib.sha256(b"test").hexdigest()
    assert len(digest) == 64


# ═══════════════════════════ SQL REGRESSION ═══════════════════════════════════


def test_no_sql_f_string_injection_in_project():
    """Sucht nach F-String SQL-Injection im Projektcode (nur execute/sql-Kontext)."""
    import glob

    violations = []
    injection_patterns = ['execute(f"', "execute(f'"]

    for fpath in glob.glob("**/*.py", recursive=True):
        if "gpt_researcher/" in fpath:
            continue
        if "__pycache__" in fpath or ".venv" in fpath:
            continue
        if "test_" in fpath:
            continue
        try:
            with open(fpath) as f:
                content = f.read()
        except Exception:
            continue

        for pattern in injection_patterns:
            if pattern in content:
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if pattern in line:
                        violations.append(f"{fpath}:{i + 1}: {line.strip()[:80]}")

    assert not violations, (
        f"Potenzielle SQL-F-String-Injection in Projektdateien: {violations}"
    )


# ═══════════════════════════ SSL VERIFY REGRESSION ═══════════════════════════


def test_no_verify_false_in_project_code():
    """Sucht nach verify=False im Projektcode.

    Erlaubte Ausnahmen: gpt_researcher/ Submodul.
    """
    import glob

    violations = []
    for fpath in glob.glob("**/*.py", recursive=True):
        if "gpt_researcher/" in fpath:
            continue
        if "__pycache__" in fpath or ".venv" in fpath:
            continue
        if "test_" in fpath:
            continue
        try:
            with open(fpath) as f:
                content = f.read()
        except Exception:
            continue
        if "verify=False" in content:
            violations.append(fpath)

    # Allowlist (currently none in project code)
    allowed = []
    actual = [v for v in violations if v not in allowed]

    assert not actual, (
        f"Projektdateien mit verify=False (außerhalb gpt_researcher/): {actual}"
    )


# ═══════════════════════════ BANDIT POLICY ═══════════════════════════════════


def test_security_policy_exists():
    """Security-Policy-Dokumentation existiert."""
    assert os.path.isfile("docs/security/bandit-triage.md"), "bandit-triage.md fehlt"
    assert os.path.isfile("docs/security/security-gate-policy.md"), (
        "security-gate-policy.md fehlt"
    )
    assert os.path.isfile("docs/security/submodule-security-review.md"), (
        "submodule-security-review.md fehlt"
    )
