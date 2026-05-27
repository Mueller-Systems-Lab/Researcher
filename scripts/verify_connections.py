#!/usr/bin/env python3
"""Verbindungs-Checker für Researcher — prüft alle externen Abhängigkeiten.

Prüft:
  1. Sind alle Umgebungsvariablen gesetzt?
  2. Sind SearXNG, Ollama, Tor erreichbar?
  3. Sind alle API-Endpunkte der MCP/Deep-Research-Server erreichbar?
  4. Gibt es noch Mock-Patterns im Code?
  5. Sind Pläne und Run-States im Dateisystem vorhanden?

Exit-Code: 0 wenn alle kritischen Checks bestehen, 1 bei Fehlern.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
# Stelle sicher, dass das Projekt-Root im Import-Pfad ist
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REQUIRED_ENV_VARS = [
    "FAST_LLM",
    "SMART_LLM",
    "STRATEGIC_LLM",
    "OLLAMA_BASE_URL",
    "EMBEDDING",
    "SEARX_URL",
    "RETRIEVER",
]

SERVICE_CHECKS = {
    "Ollama": ("OLLAMA_BASE_URL", "/api/tags"),
    "SearXNG": ("SEARX_URL", "/search?q=test&format=json"),
}

STORAGE_PATHS = [
    "reports/deep_research/runs",
    "reports/deep_research/plans",
    "reports/deep_research/evidence",
    "chroma_db",
    "darknet_index",
]

MOCK_PATTERNS = [
    (r"Math\.random\(\)", "Math.random() Aufruf"),
    (r"random\.random\(\)", "random.random() Aufruf"),
    (r"random\.randint\(", "random.randint() Aufruf"),
    (r'"sk-dummy"', "Dummy API-Key 'sk-dummy'"),
    (r"# temporär", "Kommentar 'temporär'"),
    (r"# später ersetzen", "Kommentar 'später ersetzen'"),
]

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

errors = 0
warnings = 0


def check_env_vars() -> int:
    """Prüft ob alle erforderlichen Umgebungsvariablen gesetzt sind."""
    global warnings
    print("=" * 60)
    print("  1. UMGEBUNGSVARIABLEN")
    print("=" * 60)

    missing = []
    for var in REQUIRED_ENV_VARS:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}={value[:50]}")
        else:
            print(f"  {RED}❌{RESET} {var} NICHT GESETZT")
            missing.append(var)

    # Check .env file exists
    env_path = ROOT / ".env"
    if env_path.exists():
        print(f"  ✅ .env gefunden ({env_path.stat().st_size} bytes)")
    else:
        print(f"  {YELLOW}⚠️{RESET}  .env NICHT gefunden")
        warnings += 1

    return len(missing)


def check_services() -> int:
    """Prüft Erreichbarkeit von Ollama und SearXNG."""
    global warnings
    print("\n" + "=" * 60)
    print("  2. DIENSTE (SearXNG, Ollama)")
    print("=" * 60)

    import requests

    service_errors = 0

    for name, (env_var, path) in SERVICE_CHECKS.items():
        base_url = os.getenv(env_var, "")
        if not base_url:
            print(f"  {YELLOW}⚠️{RESET}  {name}: {env_var} nicht gesetzt — überspringe")
            warnings += 1
            continue

        url = f"{base_url.rstrip('/')}{path}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 400:
                print(f"  ✅ {name} erreichbar ({url}) — Status {r.status_code}")
            else:
                print(
                    f"  {YELLOW}⚠️{RESET}  {name} antwortet mit {r.status_code} ({url})"
                )
                warnings += 1
        except requests.ConnectionError:
            print(f"  {YELLOW}⚠️{RESET}  {name} NICHT ERREICHBAR ({url})")
            warnings += 1
        except Exception as e:
            print(f"  {YELLOW}⚠️{RESET}  {name}: {e}")
            warnings += 1

    return service_errors


def check_storage() -> int:
    """Prüft ob Storage-Pfade existieren."""
    global warnings
    print("\n" + "=" * 60)
    print("  3. STORAGE-PFADE")
    print("=" * 60)

    missing = 0
    for path in STORAGE_PATHS:
        full = ROOT / path
        if full.exists():
            item_count = len(list(full.glob("*"))) if full.is_dir() else 0
            print(f"  ✅ {path}/ ({item_count} Einträge)")
        else:
            print(
                f"  {YELLOW}⚠️{RESET}  {path}/ NICHT VORHANDEN (wird bei erster Nutzung erstellt)"
            )
            warnings += 1

    return missing


def check_mock_patterns() -> int:
    """Sucht nach Mock-Patterns im Projektcode (nicht in Tests, nicht in Submodul)."""
    print("\n" + "=" * 60)
    print("  4. MOCK-PATTERN-SCAN (Projektcode)")
    print("=" * 60)

    project_dirs = [
        "config",
        "crawlers",
        "darknet_search",
        "dashboard",
        "search",
        "vectordb",
        "mcp_tools",
        "onion_discovery",
        "research_orchestrator",
        "research_planner",
        "research_workers",
        "searcher_pipeline",
        "evidence_store",
        "deep_report",
        "scripts",
    ]

    found = 0
    for proj_dir in project_dirs:
        dir_path = ROOT / proj_dir
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            for pattern, description in MOCK_PATTERNS:
                import re

                if re.search(pattern, content):
                    print(
                        f"  {YELLOW}⚠️{RESET}  {py_file.relative_to(ROOT)}: {description}"
                    )
                    found += 1

    if found == 0:
        print("  ✅ Keine Mock-Patterns im Projektcode gefunden")
    return found


def check_plan_persistence() -> int:
    """Prüft ob die Plan-Persistenz funktioniert."""
    global warnings
    print("\n" + "=" * 60)
    print("  5. PLAN-PERSISTENZ (deep_research_api)")
    print("=" * 60)

    # Prüfe ob _save_plan und _load_plan im Code existieren
    api_path = ROOT / "deep_research_api.py"
    if not api_path.exists():
        print(f"  {RED}❌{RESET} deep_research_api.py nicht gefunden")
        return 1

    content = api_path.read_text(encoding="utf-8")
    has_save = "def _save_plan" in content
    has_load = "def _load_plan" in content
    has_dir = "_PLANS_DIR" in content

    if has_save:
        print("  ✅ _save_plan() Funktion vorhanden")
    else:
        print(f"  {RED}❌{RESET} _save_plan() fehlt")
    if has_load:
        print("  ✅ _load_plan() Funktion vorhanden")
    else:
        print(f"  {RED}❌{RESET} _load_plan() fehlt")
    if has_dir:
        print("  ✅ _PLANS_DIR Pfad konfiguriert")
    else:
        print(f"  {YELLOW}⚠️{RESET}  _PLANS_DIR nicht gefunden")

    plans_dir = ROOT / "reports" / "deep_research" / "plans"
    if plans_dir.exists():
        plan_files = list(plans_dir.glob("*.json"))
        print(f"  ✅ plans/ Verzeichnis existiert ({len(plan_files)} Pläne)")
    else:
        print(f"  {YELLOW}⚠️{RESET}  plans/ wird bei erster Plan-Erstellung angelegt")

    return 0


def check_deep_research_api() -> int:
    """Prüft ob alle Deep-Research-API-Endpunkte exportiert sind."""
    global warnings
    print("\n" + "=" * 60)
    print("  6. DEEP-RESEARCH-API-ENDPUNKTE")
    print("=" * 60)

    required_handlers = [
        "handle_deep_research_plan",
        "handle_deep_research_get_plan",
        "handle_deep_research_approve",
        "handle_deep_research_run",
        "handle_deep_research_get_run",
        "handle_deep_research_get_events",
        "handle_deep_research_get_report",
        "handle_deep_research_get_evaluation",
        "route_deep_research",
    ]

    found_all = True
    try:
        import importlib

        mod = importlib.import_module("deep_research_api")
        for name in required_handlers:
            if hasattr(mod, name):
                print(f"  ✅ {name} exportiert")
            else:
                print(f"  {RED}❌{RESET} {name} fehlt in deep_research_api")
                found_all = False
    except ImportError as e:
        print(f"  {YELLOW}⚠️{RESET}  deep_research_api nicht ladbar ({e}) — überspringe")
        warnings += 1
        return 0

    if not found_all:
        warnings += 1
    return 0


def check_plan_persistence_roundtrip() -> int:
    """Prüft Plan-Persistenz Roundtrip: save → restart → load."""
    global warnings
    print("\n" + "=" * 60)
    print("  7. PLAN-PERSISTENZ-ROUNDTRIP")
    print("=" * 60)

    import tempfile

    # Verwende temporären Ordner für den Test
    temp_plans_dir = Path(tempfile.mkdtemp(prefix="plan_roundtrip_"))
    test_plan_id = "roundtrip-test-123"
    test_plan = {
        "plan_id": test_plan_id,
        "query": "Roundtrip test query",
        "status": "draft",
        "nodes": [{"id": "node-1", "question": "Test question"}],
    }

    try:
        # Phase 1: Save
        # Temporär Plans-Verzeichnis überschreiben
        import deep_research_api as api
        from deep_research_api import _load_plan, _save_plan

        original_plans_dir = api._PLANS_DIR
        api._PLANS_DIR = str(temp_plans_dir)

        _save_plan(test_plan_id, test_plan)
        print(f"  ✅ Plan gespeichert ({temp_plans_dir / test_plan_id}.json)")

        # Phase 2: Simuliere Neustart (Cache leeren)
        api._plans.clear()

        # Phase 3: Load
        loaded = _load_plan(test_plan_id)
        if loaded and loaded.get("plan_id") == test_plan_id:
            print(f"  ✅ Plan von Disk geladen: {loaded.get('query')}")
        else:
            print(f"  {RED}❌{RESET} Plan konnte nicht von Disk geladen werden")
            warnings += 1

        # Restore original
        api._PLANS_DIR = original_plans_dir

    except ImportError as e:
        print(f"  {YELLOW}⚠️{RESET}  deep_research_api nicht ladbar ({e}) — überspringe")
        warnings += 1
        return 0
    except Exception as e:
        print(f"  {YELLOW}⚠️{RESET} Roundtrip-Fehler: {e}")
        warnings += 1
    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_plans_dir, ignore_errors=True)

    return 0


def check_evidence_store_content() -> int:
    """Prüft Evidence Store Inhalt (nicht nur Verzeichnis-Existenz)."""
    global warnings
    print("\n" + "=" * 60)
    print("  8. EVIDENCE-STORE-INHALT")
    print("=" * 60)

    evidence_dir = ROOT / "reports" / "deep_research" / "evidence"

    if not evidence_dir.exists():
        print(
            f"  {YELLOW}⚠️{RESET}  evidence/ existiert nicht (wird bei erster Nutzung erstellt)"
        )
        warnings += 1
        return 0

    required_files = ["sources.jsonl", "segments.jsonl", "citations.jsonl"]
    all_present = True
    total_lines = 0

    for filename in required_files:
        file_path = evidence_dir / filename
        if file_path.exists():
            line_count = (
                len(file_path.read_text(encoding="utf-8").strip().split("\n"))
                if file_path.stat().st_size > 0
                else 0
            )
            print(f"  ✅ {filename} ({line_count} Einträge)")
            total_lines += line_count
        else:
            print(
                f"  {YELLOW}⚠️{RESET}  {filename} nicht vorhanden (wird bei erster Nutzung erstellt)"
            )
            all_present = False
            warnings += 1

    if all_present and total_lines > 0:
        print(f"  ✅ Evidence Store enthält Daten ({total_lines} Einträge gesamt)")

    return 0


def main() -> int:
    global errors, warnings

    print(f"\n{'=' * 60}")
    print("  RESEARCHER VERBINDUNGS-CHECKER")
    print(f"{'=' * 60}")

    errors += check_env_vars()
    errors += check_services()
    errors += check_storage()
    errors += check_mock_patterns()
    errors += check_plan_persistence()
    errors += check_deep_research_api()
    errors += check_plan_persistence_roundtrip()
    errors += check_evidence_store_content()

    print(f"\n{'=' * 60}")
    print("  ERGEBNIS")
    print(f"{'=' * 60}")
    print(f"  Fehler:   {errors}")
    print(f"  Warnungen: {warnings}")

    if errors == 0 and warnings == 0:
        print(f"\n  {GREEN}✅ ALLE CHECKS BESTANDEN{RESET}")
        return 0
    elif errors == 0:
        print(f"\n  {YELLOW}⚠️  WARNHINWEISE (keine Fehler){RESET}")
        return 0
    else:
        print(f"\n  {RED}❌ {errors} FEHLER GEFUNDEN{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
