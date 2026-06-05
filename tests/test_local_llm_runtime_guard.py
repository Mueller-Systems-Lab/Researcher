"""Tests für Runtime Guard — DR-08: Local Model Runtime Guard."""

from __future__ import annotations

import pytest

from config.local_llm_runtime import (
    RuntimeStatus,
    can_start_deep_research,
    check_endpoint_local,
    is_garbled,
    run_guard,
)

# ── Endpoint Checks ──────────────────────────────────────────────────────


def test_localhost_allowed():
    """127.0.0.1 ist erlaubt."""
    assert check_endpoint_local("http://127.0.0.1:8080") is True


def test_localhost_ipv6_allowed():
    """::1 (IPv6) ist erlaubt."""
    assert check_endpoint_local("http://[::1]:8080") is True


def test_cloud_openai_blocked():
    """api.openai.com wird blockiert."""
    assert check_endpoint_local("https://api.openai.com/v1") is False


def test_cloud_anthropic_blocked():
    """api.anthropic.com wird blockiert."""
    assert check_endpoint_local("https://api.anthropic.com") is False


def test_cloud_tavily_blocked():
    """api.tavily.com wird blockiert."""
    assert check_endpoint_local("https://api.tavily.com") is False


def test_external_ip_blocked():
    """Externe IP wird blockiert."""
    assert check_endpoint_local("http://192.168.1.1:8080") is False


# ── Allowlist Tests (DR-08 Extension) ─────────────────────────────────────


def test_allowlisted_lan_ip_allowed(monkeypatch):
    """Explizit erlaubte LAN-IP via LOCAL_LLM_ALLOWED_HOSTS wird akzeptiert."""
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", "192.168.43.52")
    assert check_endpoint_local("http://192.168.43.52:1234") is True


def test_non_allowlisted_lan_ip_still_blocked(monkeypatch):
    """Nicht freigegebene private IP bleibt blockiert trotz Allowlist."""
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", "192.168.43.52")
    assert check_endpoint_local("http://192.168.1.1:8080") is False


def test_allowlist_comma_separated(monkeypatch):
    """Komma-getrennte Hosts werden korrekt geparsed."""
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", "192.168.43.52,10.0.0.5")
    assert check_endpoint_local("http://192.168.43.52:1234") is True
    assert check_endpoint_local("http://10.0.0.5:8080") is True


def test_allowlist_handles_whitespace(monkeypatch):
    """Leerzeichen um Kommas werden toleriert."""
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", " 192.168.43.52 , 10.0.0.5 ")
    assert check_endpoint_local("http://192.168.43.52:1234") is True


def test_allowlist_loopback_always_works(monkeypatch):
    """Loopback funktioniert auch OHNE Env-Variable."""
    monkeypatch.delenv("LOCAL_LLM_ALLOWED_HOSTS", raising=False)
    assert check_endpoint_local("http://127.0.0.1:8080") is True
    assert check_endpoint_local("http://localhost:8080") is True


def test_allowlist_empty_env_no_break(monkeypatch):
    """Leere LOCAL_LLM_ALLOWED_HOSTS ändert nichts (kein Crash)."""
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", "")
    # Loopback muss weiterhin gehen
    assert check_endpoint_local("http://127.0.0.1:8080") is True
    # Externe IP weiterhin blockiert
    assert check_endpoint_local("http://192.168.1.1:8080") is False


def test_allow_private_lan_mode_allows_rfc1918(monkeypatch):
    """ALLOW_PRIVATE_LAN_LLM=true erlaubt RFC1918-IPs."""
    monkeypatch.setenv("ALLOW_PRIVATE_LAN_LLM", "true")
    assert check_endpoint_local("http://192.168.43.52:1234") is True
    assert check_endpoint_local("http://10.0.0.5:8080") is True
    assert check_endpoint_local("http://172.16.0.1:8080") is True


def test_private_lan_mode_still_blocks_public_ips(monkeypatch):
    """ALLOW_PRIVATE_LAN_LLM=true blockiert weiterhin öffentliche IPs."""
    monkeypatch.setenv("ALLOW_PRIVATE_LAN_LLM", "true")
    assert check_endpoint_local("http://8.8.8.8:8080") is False


def test_cloud_pattern_in_allowed_url_blocked(monkeypatch):
    """Cloud-Patterns in der URL werden geblockt, auch bei Allowlist."""
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", "192.168.43.52")
    # Cloud pattern im Pfad
    assert (
        check_endpoint_local("http://192.168.43.52:1234/proxy/api.openai.com/chat")
        is False
    )


def test_rfc1918_10_network_allowed_in_mode(monkeypatch):
    """10.x.x.x ist mit ALLOW_PRIVATE_LAN_LLM=true erlaubt."""
    monkeypatch.setenv("ALLOW_PRIVATE_LAN_LLM", "true")
    assert check_endpoint_local("http://10.0.0.1:1234") is True


def test_rfc1918_172_network_allowed_in_mode(monkeypatch):
    """172.16-31.x.x ist mit ALLOW_PRIVATE_LAN_LLM=true erlaubt."""
    monkeypatch.setenv("ALLOW_PRIVATE_LAN_LLM", "true")
    assert check_endpoint_local("http://172.16.0.1:1234") is True
    assert check_endpoint_local("http://172.31.255.254:1234") is True


def test_rfc1918_mode_all_values(monkeypatch):
    """ALLOW_PRIVATE_LAN_LLM akzeptiert true, 1, yes (case-insensitive)."""
    for value in ("true", "True", "TRUE", "1", "yes", "YES"):
        monkeypatch.setenv("ALLOW_PRIVATE_LAN_LLM", value)
        assert check_endpoint_local("http://192.168.43.52:1234") is True


def test_rfc1918_mode_false_values_block(monkeypatch):
    """ALLOW_PRIVATE_LAN_LLM=false/0/no blockiert weiterhin."""
    # Clear explicit allowlist so only the mode flag matters
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", "")
    for value in ("false", "0", "no", ""):
        monkeypatch.setenv("ALLOW_PRIVATE_LAN_LLM", value)
        assert check_endpoint_local("http://192.168.43.52:1234") is False


def test_is_rfc1918_valid():
    """_is_rfc1918 erkennt RFC1918-IPs korrekt."""
    from config.local_llm_runtime import _is_rfc1918

    assert _is_rfc1918("192.168.1.1") is True
    assert _is_rfc1918("10.0.0.1") is True
    assert _is_rfc1918("172.16.0.1") is True
    assert _is_rfc1918("8.8.8.8") is False
    assert _is_rfc1918("127.0.0.1") is False  # loopback is not RFC1918
    assert _is_rfc1918("not-an-ip") is False  # non-IP hostname
    assert _is_rfc1918("::1") is False  # IPv6
    assert _is_rfc1918("192.168.43.52") is True


def test_get_allowlisted_hosts_defaults(monkeypatch):
    """_get_allowlisted_hosts enthält immer Loopback-Hosts."""
    monkeypatch.delenv("LOCAL_LLM_ALLOWED_HOSTS", raising=False)
    from config.local_llm_runtime import _get_allowlisted_hosts

    hosts = _get_allowlisted_hosts()
    assert "127.0.0.1" in hosts
    assert "localhost" in hosts
    assert "::1" in hosts


def test_get_allowlisted_hosts_with_env(monkeypatch):
    """_get_allowlisted_hosts erweitert Loopback um Env-Werte."""
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_HOSTS", "192.168.43.52,10.0.0.5")
    from config.local_llm_runtime import _get_allowlisted_hosts

    hosts = _get_allowlisted_hosts()
    assert "127.0.0.1" in hosts
    assert "192.168.43.52" in hosts
    assert "10.0.0.5" in hosts


def test_cloud_groq_blocked():
    """Groq Cloud wird blockiert."""
    assert check_endpoint_local("https://api.groq.com") is False


def test_cloud_mistral_blocked():
    """Mistral Cloud wird blockiert."""
    assert check_endpoint_local("https://api.mistral.ai/v1") is False


# ── Garbled Detection ────────────────────────────────────────────────────


def test_garbled_empty_string():
    """Leerer Output ist garbled."""
    assert is_garbled("") is True


def test_garbled_whitespace_only():
    """Nur Whitespace ist garbled."""
    assert is_garbled("   \n  ") is True


def test_garbled_repeated_characters():
    """Wiederholte Zeichen (>20) sind garbled."""
    assert is_garbled("aaaaaaaaaaaaaaaaaaaaa") is True


def test_garbled_replacement_char():
    """Unicode Replacement Character \ufffd ist garbled."""
    assert is_garbled("Something \ufffd broken") is True


def test_garbled_null_byte():
    """Null-Byte ist garbled."""
    assert is_garbled("text\x00broken") is True


def test_clean_text_not_garbled():
    """Sauberer Text ist nicht garbled."""
    assert is_garbled("This is a normal response from the model.") is False


def test_german_text_not_garbled():
    """Deutscher Text mit Umlauten ist nicht garbled."""
    assert is_garbled("Öffentliche Förderung für KI-Startups in Österreich.") is False


# ── Status Classes ───────────────────────────────────────────────────────


def test_status_enum_values():
    """Alle Status-Klassen sind definiert."""
    assert RuntimeStatus.LOCAL_LLM_READY.value == "LOCAL_LLM_READY"
    assert RuntimeStatus.MODEL_GARBLED.value == "MODEL_GARBLED"
    assert RuntimeStatus.MODEL_TIMEOUT.value == "MODEL_TIMEOUT"
    assert RuntimeStatus.MODEL_CRASH.value == "MODEL_CRASH"
    assert RuntimeStatus.CLOUD_BLOCKED.value == "CLOUD_BLOCKED"
    assert (
        RuntimeStatus.LOCAL_OPENAI_COMPAT_ALLOWED.value == "LOCAL_OPENAI_COMPAT_ALLOWED"
    )


def test_can_start_deep_research_ready():
    """LOCAL_LLM_READY → Deep Research kann starten."""
    from config.local_llm_runtime import RuntimeGuardResult

    result = RuntimeGuardResult(status=RuntimeStatus.LOCAL_LLM_READY)
    assert can_start_deep_research(result) is True


def test_can_start_deep_research_blocked():
    """MODEL_GARBLED → Deep Research darf nicht starten."""
    from config.local_llm_runtime import RuntimeGuardResult

    result = RuntimeGuardResult(status=RuntimeStatus.MODEL_GARBLED)
    assert can_start_deep_research(result) is False


def test_can_start_deep_research_cloud():
    """CLOUD_BLOCKED → Deep Research darf nicht starten."""
    from config.local_llm_runtime import RuntimeGuardResult

    result = RuntimeGuardResult(status=RuntimeStatus.CLOUD_BLOCKED)
    assert can_start_deep_research(result) is False


# ── Guard Function (without live model) ──────────────────────────────────


def test_run_guard_cloud_endpoint_rejected():
    """run_guard blockiert Cloud-Endpoints sofort."""
    result = run_guard(
        base_url="https://api.openai.com/v1",
        model="gpt-4",
        test_generation=False,
    )
    assert result.status == RuntimeStatus.CLOUD_BLOCKED
    assert result.cloud_detected is True


def test_run_guard_nonexistent_local_handled():
    """run_guard behandelt nicht-erreichbaren localhost."""
    result = run_guard(
        base_url="http://127.0.0.1:19999",
        model="qwen3.5",
        test_generation=False,
        timeout=1.0,
    )
    assert result.status in (
        RuntimeStatus.MODEL_CRASH,
        RuntimeStatus.MODEL_TIMEOUT,
    )


def test_runtime_guard_result_has_fields():
    """RuntimeGuardResult hat alle Pflichtfelder."""
    from config.local_llm_runtime import RuntimeGuardResult

    r = RuntimeGuardResult()
    assert r.status == RuntimeStatus.LOCAL_LLM_BLOCKED
    assert r.errors == []
    assert r.warnings == []
    assert r.model == ""


def test_garbled_detects_truncated_unicode():
    """Verdächtige Unicode-Sequenzen sind garbled."""
    assert is_garbled("Hello\ufffd\ufffd\ufffdWorld") is True


# ── Additional Coverage ──────────────────────────────────────────────────


def test_endpoint_local_ipv6_bracket():
    """IPv6 mit Brackets ist local."""
    assert check_endpoint_local("http://[::1]:11434") is True


def test_endpoint_cloud_cohere_blocked():
    """Cohere Cloud wird blockiert."""
    assert check_endpoint_local("https://api.cohere.ai/v1") is False


def test_endpoint_cloud_together_blocked():
    """Together Cloud wird blockiert."""
    assert check_endpoint_local("https://api.together.xyz") is False


def test_endpoint_cloud_azure_blocked():
    """Azure OpenAI wird blockiert."""
    assert check_endpoint_local("https://openai.azure.com") is False


def test_endpoint_cloud_perplexity_blocked():
    """Perplexity Cloud wird blockiert."""
    assert check_endpoint_local("https://api.perplexity.ai") is False


def test_endpoint_cloud_google_blocked():
    """Google Generative Language wird blockiert."""
    assert check_endpoint_local("https://generativelanguage.googleapis.com") is False


def test_garbled_ratio_control_chars():
    """Hoher Anteil an Steuerzeichen → garbled."""
    text = "\x00\x01\x02\x03\x04\x05\x06\x07\x08"
    assert is_garbled(text) is True


def test_garbled_short_valid_text():
    """Kurzer valider Text ist nicht garbled."""
    assert is_garbled("OK") is False


def test_garbled_special_chars_valid():
    """Sonderzeichen in validem Text sind OK."""
    assert is_garbled("Café résumé naïve") is False


def test_can_start_local_llm_partial():
    """LOCAL_LLM_PARTIAL → Deep Research kann starten."""
    from config.local_llm_runtime import RuntimeGuardResult

    r = RuntimeGuardResult(status=RuntimeStatus.LOCAL_LLM_PARTIAL)
    assert can_start_deep_research(r) is True


def test_can_start_openai_compat():
    """LOCAL_OPENAI_COMPAT_ALLOWED → Deep Research kann starten."""
    from config.local_llm_runtime import RuntimeGuardResult

    r = RuntimeGuardResult(status=RuntimeStatus.LOCAL_OPENAI_COMPAT_ALLOWED)
    assert can_start_deep_research(r) is True


def test_can_start_timeout():
    """MODEL_TIMEOUT → Deep Research darf nicht starten."""
    from config.local_llm_runtime import RuntimeGuardResult

    r = RuntimeGuardResult(status=RuntimeStatus.MODEL_TIMEOUT)
    assert can_start_deep_research(r) is False


def test_can_start_crash():
    """MODEL_CRASH → Deep Research darf nicht starten."""
    from config.local_llm_runtime import RuntimeGuardResult

    r = RuntimeGuardResult(status=RuntimeStatus.MODEL_CRASH)
    assert can_start_deep_research(r) is False


def test_guard_result_defaults():
    """RuntimeGuardResult Default-Werte."""
    from config.local_llm_runtime import RuntimeGuardResult

    r = RuntimeGuardResult(model="qwen", endpoint="http://127.0.0.1:8080")
    assert r.model == "qwen"
    assert r.latency_ms == 0.0
    assert r.max_context == 0
    assert r.generation_sample == ""
    assert r.cloud_detected is False


def test_garbled_mixed_printable():
    """Gemischter Text mit wenigen Control-Chars ist OK."""
    text = "Normal text with\na newline and\ttab."
    assert is_garbled(text) is False


# ── _validate_url_scheme untested paths ──────────────────────────────────


def test_validate_url_scheme_file_raises():
    from config.local_llm_runtime import _validate_url_scheme

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _validate_url_scheme("file:///etc/passwd")


def test_validate_url_scheme_no_scheme_raises():
    from config.local_llm_runtime import _validate_url_scheme

    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        _validate_url_scheme("127.0.0.1:8080")


# ── check_endpoint_local cloud-pattern path ──────────────────────────────


def test_endpoint_local_cloud_pattern_in_path():
    from config.local_llm_runtime import check_endpoint_local

    assert (
        check_endpoint_local("http://127.0.0.1:11434/proxy/api.openai.com/chat")
        is False
    )


# ── check_model_present JSON parsing ─────────────────────────────────────

_MOCK_MODELS_JSON = b'{"object":"list","data":[{"id":"qwen3.5-uncensored","object":"model"},{"id":"nomic-embed-text","object":"model"}]}'


def test_check_model_present_found():
    from unittest.mock import MagicMock, patch

    from config.local_llm_runtime import check_model_present

    mock = MagicMock()
    mock.__enter__.return_value.read.return_value = _MOCK_MODELS_JSON
    with patch("urllib.request.urlopen", return_value=mock):
        ok, err = check_model_present(
            "http://127.0.0.1:8080", "qwen3.5-uncensored", timeout=1.0
        )
    assert ok is True


def test_check_model_present_not_found():
    from unittest.mock import MagicMock, patch

    from config.local_llm_runtime import check_model_present

    mock = MagicMock()
    mock.__enter__.return_value.read.return_value = _MOCK_MODELS_JSON
    with patch("urllib.request.urlopen", return_value=mock):
        ok, err = check_model_present("http://127.0.0.1:8080", "gpt-4", timeout=1.0)
    assert ok is False
    assert "gpt-4" in err


# ── check_generation ─────────────────────────────────────────────────────

_MOCK_CHAT_OK = b'{"id":"c1","object":"chat.completion","choices":[{"index":0,"message":{"role":"assistant","content":"OK"},"finish_reason":"stop"}]}'
_MOCK_CHAT_GARBLED = b'{"id":"c2","object":"chat.completion","choices":[{"index":0,"message":{"role":"assistant","content":"aaaaaaaaaaaaaaaaaaaaa"},"finish_reason":"stop"}]}'


def test_check_generation_success():
    from unittest.mock import MagicMock, patch

    from config.local_llm_runtime import check_generation

    mock = MagicMock()
    mock.__enter__.return_value.read.return_value = _MOCK_CHAT_OK
    with patch("urllib.request.urlopen", return_value=mock):
        ok, output, err, lat = check_generation(
            "http://127.0.0.1:8080", "qwen3.5", timeout=1.0
        )
    assert ok is True
    assert "OK" in output


def test_check_generation_garbled():
    from unittest.mock import MagicMock, patch

    from config.local_llm_runtime import check_generation

    mock = MagicMock()
    mock.__enter__.return_value.read.return_value = _MOCK_CHAT_GARBLED
    with patch("urllib.request.urlopen", return_value=mock):
        ok, output, err, lat = check_generation(
            "http://127.0.0.1:8080", "qwen3.5", timeout=1.0
        )
    assert ok is False
    assert err == "garbled output detected"


# ── run_guard generation branches ────────────────────────────────────────


def test_run_guard_generation_timeout():
    from unittest.mock import patch

    from config.local_llm_runtime import RuntimeStatus, run_guard

    with (
        patch("config.local_llm_runtime.check_model_present", return_value=(True, "")),
        patch(
            "config.local_llm_runtime.check_generation",
            return_value=(False, "", "timed out", 10001.0),
        ),
    ):
        result = run_guard(
            "http://127.0.0.1:8080", "qwen3.5", test_generation=True, timeout=10.0
        )
    assert result.status == RuntimeStatus.MODEL_TIMEOUT


def test_run_guard_generation_garbled():
    from unittest.mock import patch

    from config.local_llm_runtime import RuntimeStatus, run_guard

    with (
        patch("config.local_llm_runtime.check_model_present", return_value=(True, "")),
        patch(
            "config.local_llm_runtime.check_generation",
            return_value=(
                False,
                "aaaaaaaaaaaaaaaaaaaaa",
                "garbled output detected",
                500.0,
            ),
        ),
    ):
        result = run_guard(
            "http://127.0.0.1:8080", "qwen3.5", test_generation=True, timeout=10.0
        )
    assert result.status == RuntimeStatus.MODEL_GARBLED


def test_run_guard_generation_crash():
    from unittest.mock import patch

    from config.local_llm_runtime import RuntimeStatus, run_guard

    with (
        patch("config.local_llm_runtime.check_model_present", return_value=(True, "")),
        patch(
            "config.local_llm_runtime.check_generation",
            return_value=(False, "Normal output but error", "Internal failure", 500.0),
        ),
    ):
        result = run_guard(
            "http://127.0.0.1:8080", "qwen3.5", test_generation=True, timeout=10.0
        )
    assert result.status == RuntimeStatus.MODEL_CRASH


def test_run_guard_generation_ok():
    from unittest.mock import patch

    from config.local_llm_runtime import RuntimeStatus, run_guard

    with (
        patch("config.local_llm_runtime.check_model_present", return_value=(True, "")),
        patch(
            "config.local_llm_runtime.check_generation",
            return_value=(True, "OK", "", 500.0),
        ),
    ):
        result = run_guard(
            "http://127.0.0.1:8080", "qwen3.5", test_generation=True, timeout=10.0
        )
    assert result.status == RuntimeStatus.LOCAL_LLM_READY


# ── check_generation Exception Path (Lines 157-159) ─────────────────────


def test_check_generation_exception_handled():
    """check_generation: Exception during urlopen → caught, returns (False, "", str(exc), latency)."""
    from unittest.mock import patch

    from config.local_llm_runtime import check_generation

    with patch(
        "urllib.request.urlopen",
        side_effect=ConnectionRefusedError("Connection refused"),
    ):
        ok, output, err, latency = check_generation(
            "http://127.0.0.1:19999", "test-model", timeout=0.1
        )
    assert ok is False
    assert output == ""
    assert "Connection refused" in err
    assert latency >= 0
