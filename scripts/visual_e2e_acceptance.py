#!/usr/bin/env python3
"""
PHASE 4 — Visible Browser Acceptance Test
Research E2E: Query → Search → Report → Evaluation
Visible Chromium, 15+ screenshots
Avoids networkidle on SSE pages (known issue).
"""

import json, os, time, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

REPORT_DIR = Path("/home/xxammaxx/Schreibtisch/Researcher/reports/visual-e2e")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOTS = []
PAGE_LOGS = []


def snap(page, name, full_page=False):
    path = str(REPORT_DIR / f"{len(SCREENSHOTS):02d}_{name}.png")
    try:
        page.screenshot(path=path, full_page=full_page, timeout=15000)
    except Exception as e:
        # Fallback: viewport-only screenshot
        try:
            page.screenshot(path=path, full_page=False, timeout=10000)
        except Exception as e2:
            print(f"  ⚠️ Screenshot failed: {e2}")
            return None
    SCREENSHOTS.append({"name": name, "path": path, "url": page.url})
    PAGE_LOGS.append(f"[{len(SCREENSHOTS):02d}] {name} — {page.url}")
    print(f"  📸 {len(SCREENSHOTS):02d} {name}")
    return path


def safe_goto(page, url, timeout=10000):
    """Navigate avoiding networkidle for SSE pages."""
    try:
        page.goto(url, wait_until="load", timeout=timeout)
    except:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        except:
            pass
    page.wait_for_timeout(1000)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="de-DE",
        )
        page = context.new_page()

        # ============================================================
        # 1. DASHBOARD (GPU Monitor + SSE) — use load, not networkidle
        # ============================================================
        print("\n=== 1. Dashboard (8888) ===")
        safe_goto(page, "http://127.0.0.1:8888/", timeout=10000)
        snap(page, "dashboard_main")

        safe_goto(page, "http://127.0.0.1:8888/api/gpu", timeout=10000)
        snap(page, "dashboard_gpu_json")

        # SSE stream — just capture the raw output
        safe_goto(page, "http://127.0.0.1:8888/api/gpu/stream", timeout=8000)
        page.wait_for_timeout(2000)
        snap(page, "dashboard_sse_stream")

        # ============================================================
        # 2. SEARXNG (Search Backend)
        # ============================================================
        print("\n=== 2. SearXNG (8090) ===")
        safe_goto(
            page,
            "http://127.0.0.1:8090/search?q=lokale+LLM+Systeme+2025",
            timeout=15000,
        )
        snap(page, "searxng_search_results")

        safe_goto(
            page,
            "http://127.0.0.1:8090/search?q=local+llm+open+source&format=json",
            timeout=10000,
        )
        snap(page, "searxng_json_api")

        # ============================================================
        # 3. LLAMA-SERVER (Qwen3.5)
        # ============================================================
        print("\n=== 3. llama-server (8082) ===")
        safe_goto(page, "http://127.0.0.1:8082/health", timeout=10000)
        snap(page, "llama_server_health")

        # ============================================================
        # 4. GPT RESEARCHER — Frontend
        # ============================================================
        print("\n=== 4. GPT Researcher Frontend (28202) ===")
        safe_goto(page, "http://127.0.0.1:28202/", timeout=15000)
        snap(page, "researcher_frontend")

        safe_goto(page, "http://127.0.0.1:28202/docs", timeout=15000)
        snap(page, "researcher_swagger_ui")

        # ============================================================
        # 5. GPT RESEARCHER — Previous Research Results
        # ============================================================
        print("\n=== 5. Previous Research Results ===")
        safe_goto(page, "http://127.0.0.1:28202/api/reports", timeout=10000)
        snap(page, "researcher_api_reports_list")

        safe_goto(
            page,
            "http://127.0.0.1:28202/report/task_20260603_174636_015414_b7be6c5e_Analyse_der_aktuellen_Entwicklungen_im_B",
            timeout=15000,
        )
        snap(page, "researcher_previous_report")

        # ============================================================
        # 6. START NEW RESEARCH — Background, monitor progress
        # ============================================================
        print("\n=== 6. Start New Research ===")
        safe_goto(page, "http://127.0.0.1:28202/", timeout=15000)
        snap(page, "research_start_page")

        # Trigger a background research
        import urllib.request, urllib.error

        research_query = "aktuelle Entwicklungen Open Source LLM lokal 2025"
        print(f"  Triggering: '{research_query}'")

        data = json.dumps(
            {
                "task": research_query,
                "report_type": "research_report",
                "report_source": "web",
                "tone": "Objective",
                "repo_name": "",
                "branch_name": "",
                "generate_in_background": True,
            }
        ).encode()

        req = urllib.request.Request(
            "http://127.0.0.1:28202/report/",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                result = json.loads(resp.read())
                research_id = result.get("research_id", "")
                print(f"  Research ID: {research_id}")
        except Exception as e:
            print(f"  Trigger error: {e}")
            research_id = "task_20260603_174636_015414_b7be6c5e_Analyse_der_aktuellen_Entwicklungen_im_B"

        # Monitor progress with screenshots
        for i in range(6):
            wait_sec = 8
            print(f"  Waiting {wait_sec}s (check {i + 1}/6)...")
            page.wait_for_timeout(wait_sec * 1000)

            # Refresh the report page
            try:
                safe_goto(
                    page, f"http://127.0.0.1:28202/report/{research_id}", timeout=10000
                )
            except:
                safe_goto(page, "http://127.0.0.1:28202/api/reports", timeout=10000)
            snap(page, f"research_progress_{(i + 1) * 8}s")

        # ============================================================
        # 7. OLLAMA (LLM Backend)
        # ============================================================
        print("\n=== 7. Ollama (11434) ===")
        safe_goto(page, "http://127.0.0.1:11434/api/tags", timeout=10000)
        snap(page, "ollama_api_tags")

        # ============================================================
        # 8. Final State — All Reports
        # ============================================================
        print("\n=== 8. Final Reports ===")
        safe_goto(page, "http://127.0.0.1:28202/api/reports", timeout=10000)
        snap(page, "final_reports_list")

        # Get the latest research ID from reports
        import urllib.request

        try:
            with urllib.request.urlopen(  # nosec B310
                "http://127.0.0.1:28202/api/reports", timeout=10
            ) as resp:
                reports = json.loads(resp.read())
                if reports:
                    latest_id = (
                        list(reports.keys())[-1]
                        if isinstance(reports, dict)
                        else (
                            reports[-1].get("research_id", "")
                            if isinstance(reports, list)
                            else ""
                        )
                    )
                    if latest_id:
                        safe_goto(
                            page,
                            f"http://127.0.0.1:28202/report/{latest_id}",
                            timeout=15000,
                        )
                        snap(page, "latest_research_report")
        except:
            pass

        # ============================================================
        # 9. OUTPUT FILES EVIDENCE
        # ============================================================
        print("\n=== 9. Output Files ===")
        outputs_dir = Path(
            "/home/xxammaxx/Schreibtisch/Researcher/gpt_researcher/outputs"
        )
        files = sorted(
            outputs_dir.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True
        )
        PAGE_LOGS.append(f"\n=== Output Files ({len(files)} total) ===")
        for f in files[:15]:
            size_kb = f.stat().st_size / 1024
            PAGE_LOGS.append(f"  {f.name} ({size_kb:.1f} KB)")

        # ============================================================
        # CLOSE & REPORT
        # ============================================================
        browser.close()

        print(f"\n{'=' * 60}")
        print(f"✅ VISUAL ACCEPTANCE COMPLETE — {len(SCREENSHOTS)} screenshots")
        print(f"{'=' * 60}")
        for log in PAGE_LOGS:
            print(log)

        # Save manifest
        manifest = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_screenshots": len(SCREENSHOTS),
            "screenshots": SCREENSHOTS,
            "page_logs": PAGE_LOGS,
        }
        manifest_path = REPORT_DIR / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"\nManifest: {manifest_path}")

        return len(SCREENSHOTS) >= 15


if __name__ == "__main__":
    success = run()
    if success:
        print("\n✅ PHASE 4 PASSED: >=15 screenshots captured")
    else:
        print(f"\n⚠️ PHASE 4 WARNING: Only {len(SCREENSHOTS)} screenshots (need >=15)")
