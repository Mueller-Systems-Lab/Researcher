#!/usr/bin/env python3
# =============================================================================
# Live LLM Smoke-Check CLI (Phase B)
# =============================================================================
# Wraps run_live_llm_check() as a standalone CLI tool.
#
# Opt-in via Env (sonst Abbruch mit Exit-Code 0):
#   LM_STUDIO_LIVE_TEST=1
#   LOCAL_LLM_ENDPOINT=http://192.168.43.52:1234
#   LOCAL_LLM_MODEL=qwen2.5-3b-instruct
#
# Nutzung:
#   LM_STUDIO_LIVE_TEST=1 \
#   LOCAL_LLM_ENDPOINT=http://192.168.43.52:1234 \
#   LOCAL_LLM_MODEL=qwen2.5-3b-instruct \
#   python -m cli.llm_smoke
#
#   python -m cli.llm_smoke --json     # JSON-Output
#   python -m cli.llm_smoke --timeout 60  # Custom timeout
#   python -m cli.llm_smoke --keywords '{"evidence":["evidence"],"sources":["sources"]}'
#
# Env:
#   LOCAL_LLM_LATENCY_THRESHOLD_MS  — Latenz-Schwellenwert in ms (default: 30000)
# =============================================================================
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

# ── Core: run_live_llm_check (shared between CLI + pytest) ─────────────────


def run_live_llm_check(
    endpoint: str,
    model: str,
    prompt: str | None = None,
    *,
    timeout: float = 30.0,
    enable_thinking: bool = False,
    keywords: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Führe den vollständigen Live-LLM-Check aus und gib alle Ergebnisse zurück.

    Args:
        endpoint: LM-Studio- oder OpenAI-kompatibler Endpoint (http://host:port)
        model: Modell-Name (z.B. qwen2.5-3b-instruct)
        prompt: Optionaler benutzerdefinierter Prompt (sonst Evidence-Based-Research)
        timeout: HTTP-Timeout in Sekunden
        enable_thinking: Ob enable_thinking im Chat-Template aktiviert werden soll
        keywords: Optionales dict mit keyword-groups für Assertion 4.
                  Keys: Gruppenname, Values: Liste von Keywords (case-insensitive).
                  Bei None wird das Default-Set verwendet.

    Returns:
        dict mit keys: endpoint, model, endpoint_allowed, model_present,
        model_present_error, generation_ok, generation_output,
        generation_error, latency_ms, endmarker_match, keyword_checks
    """
    from config.local_llm_runtime import (
        check_endpoint_local,
        check_model_present,
        is_garbled,
    )

    result: dict[str, Any] = {
        "endpoint": endpoint,
        "model": model,
        "endpoint_allowed": False,
        "model_present": False,
        "model_present_error": "",
        "generation_ok": False,
        "generation_output": "",
        "generation_error": "",
        "latency_ms": 0.0,
        "endmarker_match": False,
        "keyword_checks": {},
    }

    # 1. Endpoint-Check via Allowlist
    result["endpoint_allowed"] = check_endpoint_local(endpoint)
    if not result["endpoint_allowed"]:
        result["generation_error"] = "Endpoint not allowed by guard"
        return result

    # 2. Model-Präsenz
    ok, err = check_model_present(endpoint, model, timeout=timeout)
    result["model_present"] = ok
    result["model_present_error"] = err
    if not ok:
        result["generation_error"] = f"Model not present: {err}"
        return result

    # 3. Generierung mit fachlichem Prompt
    if prompt is None:
        prompt = (
            "Erkläre in 2-3 Sätzen, was 'Evidence-Based Research' bedeutet "
            "und warum Quellen und Belege wichtig sind. "
            "Beende deine Antwort mit der exakten Zeile: 'ist das LLM bereit?'"
        )

    import time
    import urllib.request
    from urllib.parse import urlparse

    start = time.time()
    try:
        parsed = urlparse(endpoint)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

        url = f"{endpoint.rstrip('/')}/v1/chat/completions"
        chat_template_kwargs: dict[str, Any] = {}
        if not enable_thinking:
            chat_template_kwargs["enable_thinking"] = False

        payload = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.0,
                "chat_template_kwargs": chat_template_kwargs,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            latency = (time.time() - start) * 1000
            result["latency_ms"] = latency
            result["generation_output"] = output

            if not output or not output.strip():
                result["generation_error"] = "Empty output"
            elif is_garbled(output):
                result["generation_error"] = "Garbled output detected"
                result["generation_ok"] = False
            else:
                result["generation_ok"] = True

    except Exception as exc:
        latency = (time.time() - start) * 1000
        result["latency_ms"] = latency
        result["generation_error"] = str(exc)
        return result

    # 4. Endmarker-Prüfung
    if result["generation_ok"]:
        lines = output.strip().splitlines()
        if lines:
            result["endmarker_match"] = lines[-1].strip() == "ist das LLM bereit?"

        # 5. Keyword-Prüfung (robust, kein Volltextvergleich)
        output_lower = output.lower()
        if keywords is not None:
            # Benutzerdefinierte Keywords
            for group_name, kw_list in keywords.items():
                result["keyword_checks"][group_name] = any(
                    kw.lower() in output_lower for kw in kw_list
                )
        else:
            # Default-Keywords (auf Evidence-Based-Research-Prompt abgestimmt)
            result["keyword_checks"] = {
                "evidence": "evidence" in output_lower,
                "sources_or_quellen": any(
                    kw in output_lower for kw in ("quellen", "sources", "source")
                ),
                "belege_or_daten": any(
                    kw in output_lower for kw in ("belege", "daten", "data", "facts")
                ),
            }

    return result


# ── Skip-Logik (shared) ────────────────────────────────────────────────────


def _is_live_opt_in() -> bool:
    """Prüft, ob der Live-Test via Env-Variable aktiviert wurde."""
    return os.getenv("LM_STUDIO_LIVE_TEST", "").lower() in ("1", "true", "yes")


def _get_endpoint() -> str:
    """Liest den LM-Studio-Endpoint aus der Umgebung."""
    return os.getenv("LOCAL_LLM_ENDPOINT", "").strip()


def _get_model() -> str:
    """Liest das zu testende Modell aus der Umgebung."""
    return os.getenv("LOCAL_LLM_MODEL", "").strip()


def _get_latency_threshold_ms() -> int:
    """Liest den Latenz-Schwellenwert aus der Umgebung (default: 30000ms)."""
    return int(os.getenv("LOCAL_LLM_LATENCY_THRESHOLD_MS", "30000"))


def _live_skip_reason() -> str | None:
    """Ermittelt den Skip-Grund oder None, wenn der Test laufen soll."""
    if not _is_live_opt_in():
        return "LM_STUDIO_LIVE_TEST not set (opt-in required)"
    if not _get_endpoint():
        return "LOCAL_LLM_ENDPOINT not set"
    if not _get_model():
        return "LOCAL_LLM_MODEL not set"
    return None


# ── CLI Entry Point ─────────────────────────────────────────────────────────


def _parse_keywords_arg(raw: str | None) -> dict[str, list[str]] | None:
    """Parse --keywords JSON-String in dict[str, list[str]] oder None."""
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("keywords must be a JSON object")
        for key, val in parsed.items():
            if not isinstance(key, str):
                raise ValueError(f"keyword group key must be string, got {type(key)}")
            if not isinstance(val, list) or not all(isinstance(v, str) for v in val):
                raise ValueError(f"keyword group '{key}' value must be list of strings")
        return parsed  # type: ignore[return-value]
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON for --keywords: {exc}", file=sys.stderr)
        sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live LLM Smoke-Check — testet Endpoint → Model → Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Beispiel:
  LM_STUDIO_LIVE_TEST=1 \\
  LOCAL_LLM_ENDPOINT=http://192.168.43.52:1234 \\
  LOCAL_LLM_MODEL=qwen2.5-3b-instruct \\
  python -m cli.llm_smoke

Env-Variablen:
  LM_STUDIO_LIVE_TEST=1            Opt-in (Pflicht)
  LOCAL_LLM_ENDPOINT               LM-Studio-Endpoint (Pflicht)
  LOCAL_LLM_MODEL                  Modell-Name (Pflicht)
  LOCAL_LLM_LATENCY_THRESHOLD_MS   Latenz-Schwelle in ms (default: 30000)
  LOCAL_LLM_ALLOWED_HOSTS          Komma-getrennte erlaubte Hosts
  ALLOW_PRIVATE_LAN_LLM=true       RFC1918-LAN-IPs erlauben
""",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output als JSON (für maschinelle Verarbeitung)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP-Timeout in Sekunden (default: 30)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Benutzerdefinierter Prompt (überschreibt Default)",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        metavar="JSON",
        help=(
            'Benutzerdefinierte Keywords als JSON, z.B. \'{"topic":["word1","word2"]}\''
        ),
    )
    parser.add_argument(
        "--enable-thinking",
        action="store_true",
        help="enable_thinking im Chat-Template aktivieren",
    )
    parser.add_argument(
        "--latency-threshold",
        type=int,
        default=None,
        help=f"Latenz-Schwelle in ms (default: {_get_latency_threshold_ms()})",
    )
    args = parser.parse_args()

    # Skip-Logik
    skip = _live_skip_reason()
    if skip is not None:
        if args.json:
            print(json.dumps({"status": "skipped", "reason": skip}))
        else:
            print(f"SKIPPED: {skip}")
        sys.exit(0)

    endpoint = _get_endpoint()
    model = _get_model()

    # Keywords parsen
    kw_dict = _parse_keywords_arg(args.keywords)

    # Run check
    result = run_live_llm_check(
        endpoint,
        model,
        prompt=args.prompt,
        timeout=args.timeout,
        enable_thinking=args.enable_thinking,
        keywords=kw_dict,
    )

    # Latenz-Schwelle
    latency_threshold = (
        args.latency_threshold
        if args.latency_threshold is not None
        else _get_latency_threshold_ms()
    )
    latency_ok = result["latency_ms"] < latency_threshold

    # Build summary
    checks = {
        "endpoint_allowed": result["endpoint_allowed"],
        "model_present": result["model_present"],
        "generation_ok": result["generation_ok"],
        "endmarker_match": result["endmarker_match"],
        "keyword_checks": result["keyword_checks"],
        "latency_ok": latency_ok,
        "latency_ms": round(result["latency_ms"], 1),
        "latency_threshold_ms": latency_threshold,
    }

    # Determine exit code
    all_passed = all(
        [
            checks["endpoint_allowed"],
            checks["model_present"],
            checks["generation_ok"],
            checks["endmarker_match"],
            all(checks["keyword_checks"].values()),
            checks["latency_ok"],
        ]
    )

    if args.json:
        output = {
            "status": "pass" if all_passed else "fail",
            "endpoint": endpoint,
            "model": model,
            "checks": checks,
        }
        if not all_passed:
            output["generation_error"] = result["generation_error"]
            output["generation_output"] = result["generation_output"][:500]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print("🔍 Live LLM Smoke-Check")
        print(f"   Endpoint: {endpoint}")
        print(f"   Model:    {model}")
        print()
        endpoint_icon = "✅" if checks["endpoint_allowed"] else "❌"
        print(f"  {endpoint_icon} Endpoint allowed by guard")
        print(f"  {'✅' if checks['model_present'] else '❌'} Model present")
        print(f"  {'✅' if checks['generation_ok'] else '❌'} Generation OK")
        if result["generation_error"]:
            print(f"     Error: {result['generation_error']}")
        endmarker_icon = "✅" if checks["endmarker_match"] else "❌"
        print(f"  {endmarker_icon} Endmarker 'ist das LLM bereit?'")
        for group, ok in checks["keyword_checks"].items():
            print(f"  {'✅' if ok else '❌'} Keyword: {group}")
        print(
            f"  {'✅' if latency_ok else '❌'} Latency: {checks['latency_ms']:.0f}ms "
            f"(< {latency_threshold}ms)"
        )
        print()
        if all_passed:
            print("✅ ALL CHECKS PASSED")
        else:
            print("❌ SOME CHECKS FAILED")
            if result["generation_output"]:
                print(
                    f"\nOutput (first 200 chars): {result['generation_output'][:200]}"
                )

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
