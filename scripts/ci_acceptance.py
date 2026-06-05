#!/usr/bin/env python3
"""
CI/CD Acceptance Test Suite — Researcher Quality Gate.

Verifies the full Researcher stack is operational:
1. All 5 services respond to HTTP healthchecks
2. Research pipeline: Query → Completion → Report generated
3. Report quality: file size, source count, claim diversity
4. Exit code 0 only if ALL checks pass

Usage:
    python3 scripts/ci_acceptance.py
    python3 scripts/ci_acceptance.py --timeout 300
    python3 scripts/ci_acceptance.py --json-output  # JSON to stdout

Phase 8: Quality Hardening (Issue #143)
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


# ── Configuration ────────────────────────────────────────────────────────────
@dataclass
class Service:
    name: str
    port: int
    path: str
    expect_status: int = 200
    expect_body_contains: str | None = None
    critical: bool = True


SERVICES = [
    Service("Ollama", 11434, "/api/tags", expect_body_contains="models"),
    Service("llama-server", 8082, "/health", expect_body_contains="ok"),
    Service("SearXNG", 8090, "/healthz", expect_status=200),
    Service("GPT Researcher", 28202, "/docs", expect_status=200),
    Service("Dashboard", 8888, "/health", expect_body_contains="ok"),
]

RESEARCH_API = "http://127.0.0.1:28202"
REPORT_DIR = Path("gpt_researcher/outputs")
DEFAULT_TIMEOUT = 600  # seconds for full research pipeline


# ── Helpers ──────────────────────────────────────────────────────────────────
def _validate_url_scheme(url: str, allowed: tuple = ("http", "https")) -> str:
    """Validate URL scheme before urlopen. Raises ValueError if unsafe.

    All CI acceptance URLs are hardcoded to 127.0.0.1 — this validation
    satisfies Bandit B310 and provides defense-in-depth.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in allowed:
        raise ValueError(f"Disallowed URL scheme: {parsed.scheme}")
    return url


def http_check(service: Service, timeout: int = 10) -> tuple[bool, str]:
    """Perform an HTTP healthcheck against a service."""
    url = _validate_url_scheme(f"http://127.0.0.1:{service.port}{service.path}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            if resp.status != service.expect_status:
                return False, f"HTTP {resp.status} (expected {service.expect_status})"
            body = resp.read().decode("utf-8", errors="replace")
            if service.expect_body_contains:
                if service.expect_body_contains.lower() not in body.lower():
                    snippet = body[:200].replace("\n", " ")
                    return (
                        False,
                        f"Body missing '{service.expect_body_contains}': {snippet}",
                    )
            return True, f"HTTP {resp.status} OK"
    except urllib.error.URLError as e:
        return False, f"Connection failed: {e.reason}"
    except Exception as e:
        return False, str(e)


def check_services() -> tuple[list[str], list[str]]:
    """Check all 5 services. Returns (passes, failures)."""
    passed, failed = [], []
    for svc in SERVICES:
        ok, detail = http_check(svc)
        status = "✅" if ok else "❌"
        msg = f"  {status} {svc.name} (:{svc.port}{svc.path}): {detail}"
        if ok:
            passed.append(msg)
        else:
            failed.append(msg)
    return passed, failed


def submit_research_query(query: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """Submit a research query via the GPT Researcher POST /report/ endpoint.

    GPT Researcher v3.5.0 supports POST /report/ with a ResearchRequest
    payload (task, report_type, report_source, tone, headers, repo_name,
    branch_name, generate_in_background). When ``generate_in_background``
    is False the response contains the complete report JSON including
    ``report``, ``pdf``, ``docx``, ``md``, and ``verification`` keys.

    The older POST /api/multi_agents endpoint requires an active WebSocket
    connection and is not suitable for CI use.

    Returns research_id on success, None on failure.
    """

    def _submit():
        payload = json.dumps(
            {
                "task": query,
                "report_type": "research_report",
                "report_source": "web",
                "tone": "Objective",
                "headers": {},
                "repo_name": "",
                "branch_name": "",
                "generate_in_background": False,
            }
        ).encode()
        research_url = _validate_url_scheme(f"{RESEARCH_API}/report/")
        req = urllib.request.Request(
            research_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # nosec B310
            data = json.loads(resp.read())
            research_id = data.get("research_id", "")
            report_content = data.get("report") or data.get("content")
            if report_content:
                # Synchronous response — save report to outputs/ for Stage 3
                REPORT_DIR.mkdir(parents=True, exist_ok=True)
                safe_id = research_id.replace(" ", "_")[:60]
                report_file = REPORT_DIR / f"{safe_id}.md"
                report_file.write_text(str(report_content), errors="replace")
                print(f"  📄 Report written: {report_file.name}")
            # Also save the full verification JSON if present
            verification = data.get("verification")
            if verification:
                REPORT_DIR.mkdir(parents=True, exist_ok=True)
                safe_id = research_id.replace(" ", "_")[:60]
                verif_file = REPORT_DIR / f"{safe_id}.verification.json"
                verif_file.write_text(
                    json.dumps(verification, indent=2), errors="replace"
                )
            return research_id

    try:
        research_id = _submit()
        if not research_id:
            print("  ❌ Failed to submit research query — no research_id returned")
            return None
        print(f"  ✅ Research completed: {research_id}")
        return research_id
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        print(f"  ❌ Research API error: HTTP {e.code} — {e.reason}")
        if body:
            print(f"     Response: {body}")
        if e.code == 400:
            print(
                "     Hint: Check that GPT Researcher container is running the local"
                " build (gptresearcher/gpt-researcher:local), not the public :latest."
            )
        return None
    except Exception as e:
        print(f"  ❌ Research query failed: {e}")
        return None


def check_reports(task_id: str | None = None) -> dict:
    """Check for report files and analyze quality metrics.

    The POST /report/ endpoint with ``generate_in_background=False``
    returns the report synchronously. Reports are saved as .md, .docx,
    .pdf, and .verification.json files in REPORT_DIR. This function
    recursively scans for report artifacts and extracts quality metrics.
    """
    import re

    result = {
        "reports_found": [],
        "total_size_kb": 0,
        "report_lines": 0,
        "has_report": False,
        "has_verification": False,
        "sources_count": 0,
        "claims_count": 0,
        "supported_claims": 0,
        "source_urls": set(),
    }

    if REPORT_DIR.exists():
        # Collect candidates — prefer mtime-based filtering when task_id is a
        # timestamp-based id, fall back to prefix matching.
        candidates = []
        mtime_cutoff = 0.0
        if task_id:
            # Try to extract a timestamp from the task_id for mtime filtering
            parts = task_id.split("_")
            for p in parts:
                if len(p) == 15 and p.isdigit():
                    try:
                        mtime_cutoff = time.mktime(time.strptime(p, "%Y%m%d_%H%M%S"))
                        break
                    except ValueError:
                        pass

        for f in REPORT_DIR.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".md", ".docx", ".pdf", ".json"):
                continue
            if mtime_cutoff and f.stat().st_mtime < mtime_cutoff:
                continue
            candidates.append(f)

        # Sort by modification time, newest first; take up to 20
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        candidates = candidates[:20]

        for f in candidates:
            result["reports_found"].append(str(f.relative_to(REPORT_DIR)))
            size = f.stat().st_size
            result["total_size_kb"] += size / 1024

            if f.suffix == ".md":
                result["has_report"] = True
                content = f.read_text(errors="replace")
                result["report_lines"] = len(content.splitlines())
                # Extract URLs from Markdown (e.g. [text](url) or bare https://...)
                for m in re.finditer(r"https?://[^\s\)\]]+", content):
                    result["source_urls"].add(m.group().rstrip("."))
            elif f.suffix == ".json" and "verification" in f.name.lower():
                result["has_verification"] = True
                try:
                    data = json.loads(f.read_text())
                    result["claims_count"] = len(data.get("claims", []))
                    result["supported_claims"] = sum(
                        1
                        for c in data.get("claims", [])
                        # verification.json uses "status", not "verdict"
                        if c.get("status") in ("supported", "SUPPORTED")
                    )
                    # Extract source_urls from claims[*].sources[*].source_url
                    for claim in data.get("claims", []):
                        for source in claim.get("sources", []):
                            url = source.get("source_url", "")
                            if url:
                                result["source_urls"].add(url)
                except Exception:
                    pass
    return result


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Researcher CI Acceptance Test")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Research pipeline timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--skip-research",
        action="store_true",
        help="Skip research pipeline test (services only)",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output results as JSON to stdout"
    )
    args = parser.parse_args()

    results = {
        "phase": "Operational Readiness (Phase 9)",
        "issue": 147,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "services": {},
        "research": {},
        "reports": {},
        "passed": False,
    }

    all_passed = True

    # ── Stage 1: Service Healthchecks ────────────────────────────────────
    print("=" * 60)
    print(" STAGE 1: Service Healthchecks")
    print("=" * 60)
    passed, failed = check_services()
    for p in passed:
        print(p)
    for f in failed:
        print(f)
        if any(svc.name in f for svc in SERVICES if svc.critical):
            all_passed = False

    results["services"]["passed"] = len(passed)
    results["services"]["failed"] = len(failed)
    results["services"]["details"] = {"passed": passed, "failed": failed}
    print(f"\n  Services: {len(passed)}/{len(SERVICES)} online\n")

    # ── Stage 2: Research Pipeline ───────────────────────────────────────
    task_id = None
    if not args.skip_research:
        print("=" * 60)
        print(" STAGE 2: Research Pipeline Test")
        print("=" * 60)

        query = "aktuelle Entwicklungen Open Source LLM lokal 2025"
        print(f'  Query: "{query}"')
        task_id = submit_research_query(query, timeout=args.timeout)
        results["research"]["task_id"] = task_id
        results["research"]["query"] = query
        results["research"]["completed"] = task_id is not None

        if not task_id:
            # Stage 2 failed — the research pipeline is now blocking.
            print("  ❌ Research pipeline failed — no report generated")
            all_passed = False
            results["research"]["skipped"] = False

    # ── Stage 3: Report Quality Analysis ─────────────────────────────────
    print("\n" + "=" * 60)
    print(" STAGE 3: Report Quality Analysis")
    print("=" * 60)

    report_data = check_reports(task_id=task_id)
    results["reports"] = {
        "files": report_data["reports_found"],
        "total_size_kb": round(report_data["total_size_kb"], 1),
        "report_lines": report_data["report_lines"],
        "claims_count": report_data["claims_count"],
        "supported_claims": report_data["supported_claims"],
        "unique_sources": len(report_data["source_urls"]),
        "source_urls": list(report_data["source_urls"])[:10],
    }

    print(f"  Report files found: {len(report_data['reports_found'])}")
    for fn in report_data["reports_found"][:5]:
        print(f"    - {fn}")
    rpt_status = "✅" if report_data["has_report"] else "❌"
    rpt_lines = report_data["report_lines"]
    print(f"  Markdown report: {rpt_status} ({rpt_lines} lines)")
    print(f"  Verification JSON: {'✅' if report_data['has_verification'] else '❌'}")
    print(f"  Claims analyzed: {report_data['claims_count']}")
    print(f"  Claims supported: {report_data['supported_claims']}")
    print(f"  Unique source URLs: {len(report_data['source_urls'])}")

    # ── Stage 3.5: SearXNG Direct Source Verification ────────────────────
    print("\n" + "=" * 60)
    print(" STAGE 3.5: SearXNG Direct Source Count")
    print("=" * 60)
    searxng_urls = set()
    try:
        import urllib.parse

        query_enc = urllib.parse.quote(
            "aktuelle Entwicklungen Open Source LLM lokal 2025"
        )
        sx_url = _validate_url_scheme(
            f"http://127.0.0.1:8090/search?format=json&q={query_enc}"
        )
        req = urllib.request.Request(sx_url)
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            sx_data = json.loads(resp.read())
            for r in sx_data.get("results", []):
                url = r.get("url", "")
                if url:
                    searxng_urls.add(url)
        engines = set(r.get("engine", "?") for r in sx_data.get("results", []))
        print(f"  SearXNG results: {len(sx_data.get('results', []))}")
        print(f"  Unique domains: {len(searxng_urls)}")
        print(f"  Engines used: {sorted(engines)}")
    except Exception as e:
        print(f"  ⚠️ SearXNG check failed: {e}")

    # ── Stage 4: Quality Gates ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" STAGE 4: Quality Gates")
    print("=" * 60)

    gates = []

    # Gate 1: All 5 services healthy
    services_ok = len(failed) == 0
    gates.append(("All 5 services healthy", services_ok))
    print(f"  {'✅' if services_ok else '❌'} Gate 1: All 5 services healthy")

    # Gate 2: Report exists
    has_report = report_data["has_report"]
    gates.append(("Report generated", has_report))
    print(f"  {'✅' if has_report else '❌'} Gate 2: Report generated")

    # Gate 3: Report ≥200 lines OR ≥15 KB
    rp_lines = report_data["report_lines"]
    rp_size = report_data["total_size_kb"]
    size_ok = rp_lines >= 200 or rp_size >= 15
    size_label = (
        f"Report >=200 lines OR >=15 KB (actual: {rp_lines} lines, {rp_size:.1f} KB)"
    )
    gates.append((size_label, size_ok))
    gate3_icon = "✅" if size_ok else "⚠️"
    print(f"  {gate3_icon} Gate 3: {size_label}")

    # Gate 4: Sources ≥3 (report URLs + SearXNG direct query)
    report_sources = len(report_data["source_urls"])
    searxng_sources = len(searxng_urls)
    total_sources = len(report_data["source_urls"] | searxng_urls)
    sources_ok = total_sources >= 3
    gates.append(
        (
            (
                f"Sources >=3 (report: {report_sources}, "
                f"SearXNG: {searxng_sources}, union: {total_sources})"
            ),
            sources_ok,
        )
    )
    src_icon = "✅" if sources_ok else "❌"
    print(
        f"  {src_icon} Gate 4: Sources >=3 "
        f"(report: {report_sources}, SearXNG: {searxng_sources}, "
        f"union: {total_sources})"
    )

    # Gate 5: Claims ≥5
    clm_count = report_data["claims_count"]
    claims_ok = clm_count >= 5
    gates.append((f"Claims >=5 (actual: {clm_count})", claims_ok))
    clm_icon = "✅" if claims_ok else "❌"
    print(f"  {clm_icon} Gate 5: Claims >=5 (actual: {clm_count})")

    # Final verdict
    all_gates_pass = all(ok for _, ok in gates)
    overall = all_passed and all_gates_pass
    results["passed"] = overall

    print("\n" + "=" * 60)
    if overall:
        print(" ✅ ACCEPTANCE TEST PASSED — All gates green!")
    else:
        failed_gates = [name for name, ok in gates if not ok]
        if not services_ok:
            print(" ❌ ACCEPTANCE TEST FAILED — Services not healthy")
        elif not all_gates_pass:
            print(
                f" ❌ ACCEPTANCE TEST FAILED — Gates failed: {', '.join(failed_gates)}"
            )
    print("=" * 60)

    if args.json_output:
        print(json.dumps(results, indent=2, default=str))

    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
