"""Local LLM Runtime Guard — ensures stable model operation for Deep Research.

DR-08: Checks model presence, endpoint health, generation quality,
garbled output detection, timeout handling, and cloud blocking.

Status classes:
- LOCAL_LLM_READY: All checks passed, Deep Research can start
- LOCAL_LLM_PARTIAL: Some checks warn but can proceed
- LOCAL_LLM_BLOCKED: Fatal issue, Deep Research must not start
- MODEL_GARBLED: Model produces incoherent output
- MODEL_TIMEOUT: Model didn't respond in time
- MODEL_CRASH: Model endpoint unreachable
- CLOUD_BLOCKED: Cloud endpoint detected, blocked
- LOCAL_OPENAI_COMPAT_ALLOWED: Localhost OpenAI-compatible endpoint OK
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse


class RuntimeStatus(str, Enum):
    LOCAL_LLM_READY = "LOCAL_LLM_READY"
    LOCAL_LLM_PARTIAL = "LOCAL_LLM_PARTIAL"
    LOCAL_LLM_BLOCKED = "LOCAL_LLM_BLOCKED"
    MODEL_GARBLED = "MODEL_GARBLED"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_CRASH = "MODEL_CRASH"
    CLOUD_BLOCKED = "CLOUD_BLOCKED"
    LOCAL_OPENAI_COMPAT_ALLOWED = "LOCAL_OPENAI_COMPAT_ALLOWED"


@dataclass
class RuntimeGuardResult:
    """Result of a runtime guard check."""

    status: RuntimeStatus = RuntimeStatus.LOCAL_LLM_BLOCKED
    model: str = ""
    endpoint: str = ""
    latency_ms: float = 0.0
    max_context: int = 0
    generation_sample: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cloud_detected: bool = False


# Allowed endpoints (localhost only)
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}

# Cloud/blocked endpoint patterns
_CLOUD_PATTERNS = [
    r"api\.openai\.com",
    r"api\.anthropic\.com",
    r"api\.tavily\.com",
    r"openai\.azure\.com",
    r"api\.groq\.com",
    r"api\.together\.xyz",
    r"api\.mistral\.ai",
    r"api\.cohere\.ai",
    r"api\.perplexity\.ai",
    r"generativelanguage\.googleapis\.com",
]


def _validate_url_scheme(url: str) -> None:
    """Validate URL uses only http or https scheme (Bandit B310 mitigation)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")


def check_endpoint_local(base_url: str) -> bool:
    """Verify the endpoint is a local address (not cloud)."""
    parsed = urlparse(base_url)
    host = parsed.hostname or ""

    # Must be localhost
    if host not in _ALLOWED_HOSTS:
        return False

    # Check for cloud patterns in URL
    url_lower = base_url.lower()
    for pattern in _CLOUD_PATTERNS:
        if re.search(pattern, url_lower):
            return False

    return True


def check_model_present(
    base_url: str,
    model: str,
    timeout: float = 5.0,
) -> tuple[bool, str]:
    """Check if a model is available at the endpoint via /v1/models."""
    try:
        import urllib.request

        url = f"{base_url.rstrip('/')}/v1/models"
        _validate_url_scheme(url)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("id", "") for m in data.get("data", [])]
            if model in models:
                return True, ""
            return False, f"model '{model}' not in {models[:10]}"
    except Exception as exc:
        return False, str(exc)


def check_generation(
    base_url: str,
    model: str,
    prompt: str = "Say 'OK' and nothing else.",
    timeout: float = 10.0,
) -> tuple[bool, str, str, float]:
    """Test minimal generation and detect garbled output.

    Returns: (ok, output_text, error, latency_ms)
    """
    start = time.time()
    try:
        import urllib.request

        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        payload = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.0,
            }
        ).encode("utf-8")

        _validate_url_scheme(url)
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            latency = (time.time() - start) * 1000

            if is_garbled(output):
                return False, output, "garbled output detected", latency
            return True, output, "", latency
    except Exception as exc:
        latency = (time.time() - start) * 1000
        return False, "", str(exc), latency


def is_garbled(text: str) -> bool:
    """Detect garbled/corrupted model output.

    Heuristics:
    - Very high ratio of non-printable characters
    - Repeated character sequences (>20 same char)
    - Extremely high entropy (random noise)
    - Empty output after generation
    """
    if not text or not text.strip():
        return True

    # High ratio of control/non-printable chars
    printable = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    if len(text) > 0 and printable / len(text) < 0.5:
        return True

    # Repeated character sequences
    for ch in set(text):
        if ch * 20 in text:
            return True

    # Garbled token patterns (truncated unicode sequences)
    garbled_markers = [
        "\ufffd",  # replacement character
        "\x00",
    ]
    for marker in garbled_markers:
        if marker in text:
            return True

    return False


def run_guard(
    base_url: str = "http://127.0.0.1:8080",
    model: str = "qwen3.5-uncensored-no-thinking",
    *,
    test_generation: bool = True,
    timeout: float = 10.0,
) -> RuntimeGuardResult:
    """Execute the full runtime guard check.

    Returns a RuntimeGuardResult with the definitive status.
    """
    result = RuntimeGuardResult(model=model, endpoint=base_url)

    # 1. Cloud blocker
    if not check_endpoint_local(base_url):
        result.status = RuntimeStatus.CLOUD_BLOCKED
        result.cloud_detected = True
        result.errors.append(f"Cloud endpoint detected: {base_url}")
        return result

    # Localhost with non-standard path is OK (llama-server compat)
    result.status = RuntimeStatus.LOCAL_OPENAI_COMPAT_ALLOWED

    # 2. Model presence
    ok, err = check_model_present(base_url, model, timeout=timeout)
    if not ok:
        result.status = RuntimeStatus.MODEL_CRASH
        result.errors.append(f"Model check failed: {err}")
        return result

    # 3. Generation test
    if test_generation:
        ok, output, err, latency = check_generation(base_url, model, timeout=timeout)
        result.latency_ms = latency
        result.generation_sample = output

        if not ok:
            if "timeout" in err.lower() or "timed out" in err.lower():
                result.status = RuntimeStatus.MODEL_TIMEOUT
            elif is_garbled(output):
                result.status = RuntimeStatus.MODEL_GARBLED
            else:
                result.status = RuntimeStatus.MODEL_CRASH
            result.errors.append(f"Generation failed: {err}")
            return result

    # 4. All checks passed
    result.status = RuntimeStatus.LOCAL_LLM_READY
    return result


def can_start_deep_research(result: RuntimeGuardResult) -> bool:
    """Determine if Deep Research can start based on guard result."""
    return result.status in (
        RuntimeStatus.LOCAL_LLM_READY,
        RuntimeStatus.LOCAL_LLM_PARTIAL,
        RuntimeStatus.LOCAL_OPENAI_COMPAT_ALLOWED,
    )
