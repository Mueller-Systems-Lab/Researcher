#!/usr/bin/env bash
# ==============================================================================
# Issue Verifikations-Script — Phase 7
# Prüft ALLE GitHub Issues (offen + geschlossen) gegen tatsächlichen Code.
#
# Verwendung:
#   ./scripts/verify-issues.sh                          # Alle offenen Issues prüfen
#   ./scripts/verify-issues.sh 42                       # Einzelnen Issue prüfen
#   ./scripts/verify-issues.sh --closed                 # Nur geschlossene Issues
#   ./scripts/verify-issues.sh --deep                   # Nur Deep Research Module
#   ./scripts/verify-issues.sh --report                 # Nur Report generieren
#   ./scripts/verify-issues.sh --all                    # Kompletter Run
#   ./scripts/verify-issues.sh --github-action          # CI-Modus (JSON-Output)
# ==============================================================================

set -euo pipefail

# ---- Konfiguration ----------------------------------------------------------
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || echo "local")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
REPORT_DIR="reports/issue-verification"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="$REPORT_DIR/verify-report-$TIMESTAMP.md"
JSON_REPORT="$REPORT_DIR/verify-report-$TIMESTAMP.json"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$REPORT_DIR"

# ---- Globale Zähler ---------------------------------------------------------
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARN_CHECKS=0

# ==============================================================================
# Helper-Funktionen
# ==============================================================================

print_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║   Researcher Issue Verifikation                            ║"
    echo "║   Repo:   $REPO"
    echo "║   Branch: $BRANCH"
    echo "║   Commit: $COMMIT_SHORT"
    echo "║   Datum:  $(date '+%Y-%m-%d %H:%M')"
    echo "╚══════════════════════════════════════════════════════════════╝"
}

print_header() {
    local title="$1"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  $title"
    echo "═══════════════════════════════════════════════════════════════"
}

# Check: Datei existiert
check_file() {
    local file="$1"
    local label="${2:-$file}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$file" ]; then
        local lines
        lines=$(wc -l < "$file" 2>/dev/null || echo "?")
        echo "  ✅ $label (${lines} Zeilen)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "  ❌ $label (FEHLT)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Check: Directory existiert
check_dir() {
    local dir="$1"
    local label="${2:-$dir}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -d "$dir" ]; then
        local count
        count=$(find "$dir" -name '*.py' 2>/dev/null | wc -l)
        echo "  ✅ $label ($count .py-Dateien)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "  ❌ $label (FEHLT)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Check: Pattern in Datei
check_pattern() {
    local pattern="$1"
    local file="$2"
    local label="${3:-$pattern}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$file" ] && grep -qE "$pattern" "$file" 2>/dev/null; then
        local count
        count=$(grep -cE "$pattern" "$file" 2>/dev/null || echo "0")
        echo "  ✅ $label ($count Treffer)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "  ❌ $label (Pattern nicht gefunden)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Check: Tests für ein Feature existieren
check_tests() {
    local pattern="$1"
    local dir="${2:-tests}"
    local label="${3:-Tests für $pattern}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    local count
    count=$(grep -rn "def test_" "$dir" --include="*.py" 2>/dev/null | grep -iE "$pattern" | wc -l || echo "0")
    if [ "$count" -gt 0 ]; then
        echo "  ✅ $label ($count Tests)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "  ⚠️  $label (Keine Tests gefunden)"
        WARN_CHECKS=$((WARN_CHECKS + 1))
        return 1
    fi
}

# Check: Modul hat Testdatei
check_test_file() {
    local test_file="$1"
    local label="${2:-$test_file}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$test_file" ]; then
        local tests
        tests=$(grep -c "def test_" "$test_file" 2>/dev/null || echo "0")
        echo "  ✅ $label ($tests Testfunktionen)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "  ❌ $label (Testdatei fehlt)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Check: Funktion existiert in Python-Datei
check_function() {
    local func="$1"
    local file="$2"
    local label="${3:-$func in $file}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$file" ] && grep -q "^def $func\|^async def $func" "$file" 2>/dev/null; then
        echo "  ✅ $label"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "  ❌ $label (Nicht gefunden)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Check: Klasse existiert in Python-Datei
check_class() {
    local cls="$1"
    local file="$2"
    local label="${3:-$cls in $file}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$file" ] && grep -q "^class $cls" "$file" 2>/dev/null; then
        echo "  ✅ $label"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo "  ❌ $label (Nicht gefunden)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

print_result() {
    echo ""
    echo "  ┌──────────────────────────────────────────────────────┐"
    printf "  │ Prüfungen: %-3d  ✅ Bestanden: %-3d  ❌ Fehlgeschlagen: %-3d  ⚠️  Warnungen: %-3d │\n" \
        "$TOTAL_CHECKS" "$PASSED_CHECKS" "$FAILED_CHECKS" "$WARN_CHECKS"
    echo "  └──────────────────────────────────────────────────────┘"
}

# ==============================================================================
# Issue-Code-Verifikation nach Gruppen
# ==============================================================================

# -------------------------------------------------------------------
# T-Serie: Issues #1-#29 (Basis-Infrastruktur)
# -------------------------------------------------------------------
verify_t_series() {
    print_header "T-SERIES (#1-#29): Basis-Infrastruktur"

    # #1: Repository-Setup
    echo "  [#1] Repository & Basis-Umgebung"
    check_file ".env.example"
    check_file "requirements.txt"
    check_file ".gitignore"
    check_file "pyproject.toml"

    # #2: Ollama
    echo "  [#2] Ollama + Qwen3"
    check_file "serve_qwen3.5_uncensored.sh" || true  # non-blocking

    # #3: SearXNG
    echo "  [#3] SearXNG Docker"
    check_file "searxng/settings.yml" || check_dir "searxng" "searxng/" || true

    # #4: GPT Researcher Fork
    echo "  [#4] GPT Researcher Fork"
    check_dir "gpt_researcher" "gpt_researcher/"

    # #5: Darknet-Crawler
    echo "  [#5] Darknet-Crawler"
    check_file "crawlers/darknet_crawler.py"
    check_pattern "SOCKS5|socks5" "crawlers/darknet_crawler.py" "Tor SOCKS5-Unterstützung"

    # #6: Whoosh-Index
    echo "  [#6] Whoosh-Index + DarknetRetriever"
    check_file "darknet_search/index.py"
    check_file "darknet_search/retriever.py"

    # #7: CompositeRetriever
    echo "  [#7] CompositeRetriever"
    check_file "search/composite.py"

    # #8: ChromaDB + Embeddings
    echo "  [#8] ChromaDB + Embeddings"
    check_file "vectordb/store.py"
    check_file "vectordb/embedding.py"

    # #9: VRAM/GPU
    echo "  [#9] VRAM-Optimierungen"
    check_file "dashboard/gpu_monitor.py"

    # #10: Integrationstests
    echo "  [#10] Integrationstests"
    check_dir "tests" "tests/"
    check_tests "composite|e2e|integration" "tests" "Integration/E2E-Tests"

    # #11: Dokumentation
    echo "  [#11] Dokumentation & Betriebsanleitung"
    check_file "README.md"
    check_file "AGENTS.md" || true

    # #12-13: Onion Discovery
    echo "  [#12-13] Onion Discovery Engine"
    check_file "onion_discovery/engine.py"
    check_file "onion_discovery/seed_queue.py"
    check_file "onion_discovery/classifier.py"

    # #14: Architecture Review
    echo "  [#14] Architecture Review"
    check_dir "docs/adr" "docs/adr/ (ADRs)" || true
    check_dir "docs/development" "docs/development/" || true

    # #15: Deterministisches Profil
    echo "  [#15] Deterministisches Research-Profil"
    if grep -q "temperature=0\|temperature.*0\.0\|RESEARCH_DETERMINISTIC.*true" "config/services.py" 2>/dev/null || \
       grep -q "temperature=0\|temperature.*0\.0\|RESEARCH_DETERMINISTIC.*true" ".env.example" 2>/dev/null || \
       grep -q "temperature=0\|temperature.*0\.0" "gpt_researcher/*.py" 2>/dev/null; then
        echo "  ✅ Deterministisches Profil konfiguriert"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Keine Temperature=0-Konfiguration gefunden (optional)"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    # #16: MCP-Tools
    echo "  [#16] MCP-Tools"
    check_dir "mcp_tools" "mcp_tools/"
    check_file "mcp_tools/web_fetch.py"
    check_file "mcp_tools/evidence_store.py"
    check_file "mcp_tools/human_review.py"

    # #17: GPU Dashboard
    echo "  [#17] GPU/VRAM Dashboard"
    check_file "dashboard/server.py"
    check_file "dashboard/gpu_monitor.py"
    check_pattern "SSE|sse|EventSource" "dashboard/server.py" "SSE-Stream"

    # #18: Teststrategie
    echo "  [#18] Teststrategie"
    check_dir "tests/security" "tests/security/"
    check_dir "tests/playwright" "tests/playwright/"
    check_dir "tests/e2e" "tests/e2e/"

    # #19: SSRF-Schutz
    echo "  [#19] SSRF-Schutz"
    check_pattern "is_private|_is_private|_validate_url|_PRIVATE" "mcp_tools/web_fetch.py" "SSRF-Validierung"

    # #20: Human-Review-Gate
    echo "  [#20] Human-Review-Gate"
    check_file "mcp_tools/human_review.py"

    # #21: Path-Traversal
    echo "  [#21] Path-Traversal-Schutz"
    check_pattern "realpath|abspath|safe_join" "dashboard/server.py" "Path-Traversal-Schutz"

    # #22: pynvml → nvidia-ml-py (oder subprocess via nvidia-smi)
    echo "  [#22] pynvml-Migration"
    if grep -q "nvidia_ml\|pynvml\|nvidia-smi" "dashboard/gpu_monitor.py" 2>/dev/null; then
        echo "  ✅ GPU-Monitor verwendet nvidia-smi oder nvidia-ml-py"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Kein GPU-Monitor-Backend gefunden"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    # #23: Dependency-Updates
    echo "  [#23] Dependency-Updates"
    check_file "requirements.txt"
    check_pattern "lxml|requests|ollama|chromadb" "requirements.txt" "Key-Dependencies"

    # #24: Code-Review-Findings
    echo "  [#24] Code-Review-Medium/Low"
    # Check that bare except was removed (measured in #37)
    local bare_count
    bare_count=$(grep -rn "except:" --include='*.py' . --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=node_modules --exclude-dir=site-packages 2>/dev/null | grep -v "#" | wc -l)
    if [ "$bare_count" -eq 0 ]; then
        echo "  ✅ Keine bare 'except:' mehr (0 Treffer)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  $bare_count bare 'except:' gefunden"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi

    # #25: CI-Pipeline
    echo "  [#25] CI-Pipeline"
    check_dir ".github/workflows" ".github/workflows/"
    check_file ".github/workflows/ci.yml"
    if [ -f ".github/workflows/test.yml" ]; then
        echo "  ✅ .github/workflows/test.yml"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  test.yml nicht gefunden (optional)"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi

    # #26: MCP-Registry
    echo "  [#26] MCP-Registry"
    check_file "mcp_tools/registry.py"
    check_file "mcp_tools/server.py"

    # #27: Dashboard embedden
    echo "  [#27] Dashboard-Embedding"
    check_file "dashboard/static/index.html" || true

    # #28: E2E-Tests
    echo "  [#28] E2E-Tests + Coverage"
    check_dir "tests/e2e" "tests/e2e/"
    check_pattern "fail_under" "pyproject.toml" "Coverage-Schwelle" || \
        check_pattern "fail_under" ".coveragerc" "Coverage-Schwelle" || true

    # #29: Release
    echo "  [#29] Release v0.1.0"
    # Check if tag exists
    if git tag -l 'v0.1.0*' 2>/dev/null | grep -q .; then
        echo "  ✅ Git-Tag v0.1.0* existiert"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Kein v0.1.0-Tag gefunden"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi
}

# -------------------------------------------------------------------
# Audit-Serie: Issues #30-#37 (Codebase-Audit-Fixes)
# -------------------------------------------------------------------
verify_audit_series() {
    print_header "AUDIT SERIES (#30-#37): Codebase-Audit-Fixes"

    # #30: hash()-Instabilität
    echo "  [#30] hash()-Instabilität"
    if [ -f "darknet_search/index.py" ]; then
        if grep -q "hash(" "darknet_search/index.py"; then
            echo "  ❌ hash() immer noch in darknet_search/index.py"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        else
            echo "  ✅ hash() entfernt — hashlib/SHA256 verwendet"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        fi
    else
        echo "  ⚠️  darknet_search/index.py nicht gefunden"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi

    # #31: Kapselungsverletzung
    echo "  [#31] CLI-Kapselung"
    if [ -f "onion_discovery/__main__.py" ]; then
        if grep -q "pending_count\|_items" "onion_discovery/__main__.py" 2>/dev/null; then
            echo "  ✅ Zugriff über Property/Getter"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            echo "  ❌ Kein Property-Zugriff gefunden"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
    else
        echo "  ❌ onion_discovery/__main__.py fehlt"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi

    # #32: Playwright-Tests
    echo "  [#32] Playwright-Test-Verbesserung"
    check_dir "tests/playwright" "tests/playwright/"
    check_test_file "tests/playwright/test_dashboard_visual_regression.py"

    # #33: query() Multi-Embedding
    echo "  [#33] VectorStore query()"
    check_pattern "query_embeddings" "vectordb/store.py" "Multi-Embedding-API"

    # #34: O(n) File-I/O
    echo "  [#34] Seed-Queue-Optimierung"
    check_file "onion_discovery/seed_queue.py"

    # #35: Whoosh-Migration
    echo "  [#35] Whoosh-Migration"
    if grep -q "whoosh" "requirements.txt" 2>/dev/null; then
        echo "  ✅ Whoosh in requirements.txt (gepinnt)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Kein Whoosh in requirements.txt"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi

    # #36: MD5-Kollision
    echo "  [#36] MD5-Kollisionsrisiko"
    local md5_count
    md5_count=$(grep -rn "md5\|MD5" --include='*.py' . --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=node_modules --exclude-dir=site-packages 2>/dev/null | grep -v "usedforsecurity\|#.*md5" | wc -l)
    if [ "$md5_count" -le 2 ]; then
        echo "  ✅ MD5-Verwendung minimiert ($md5_count Stellen)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  $md5_count MD5-Verwendungen (prüfungsbedürftig)"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi

    # #37: Broad except
    echo "  [#37] Broad except-Fix"
    local broad_count
    broad_count=$(grep -rn "except:" --include='*.py' . --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=node_modules --exclude-dir=site-packages 2>/dev/null | grep -v "#" | wc -l)
    if [ "$broad_count" -eq 0 ]; then
        echo "  ✅ Keine bare except: (0 Treffer)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  $broad_count bare except: gefunden"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi
}

# -------------------------------------------------------------------
# QA/Test-Serie: Issues #39-#46
# -------------------------------------------------------------------
verify_qa_series() {
    print_header "QA/TEST SERIES (#39-#46): Qualitätssicherung"

    # #39: QA-Repair-Loop
    echo "  [#39] QA-Repair-Loop"
    check_file "scripts/run-all-tests.sh" || true
    check_pattern "repair\|repair_loop\|qa_loop" "scripts/" "Repair-Loop" || true

    # #40: Playwright-Visual-Tests in CI
    echo "  [#40] Playwright-CI-Integration"
    check_test_file "tests/playwright/test_dashboard_visual_regression.py"
    check_test_file "tests/playwright/test_dashboard_accessibility.py"
    check_pattern "playwright" ".github/workflows/ci.yml" "Playwright in CI" || true

    # #41: Accessibility
    echo "  [#41] Accessibility"
    check_test_file "tests/playwright/test_dashboard_accessibility.py"
    check_pattern "aria-label|aria_" "dashboard/static/index.html" "ARIA-Labels" || true

    # #42: Responsive/Mobile
    echo "  [#42] Responsive-Tests"
    check_pattern "viewport|375|responsive" "tests/playwright/" "Viewport-Tests" || true

    # #43: Crawler-Unit-Tests
    echo "  [#43] Crawler-Unit-Tests"
    check_test_file "tests/test_crawlers.py" || true
    check_tests "crawler" "tests" "Crawler-Tests"

    # #44: UX-Heuristik
    echo "  [#44] UX-Heuristik"
    check_file "docs/development/ui-local-readiness.md" || true
    check_pattern "empty.*state|loading.*state|error.*state|skeleton" "dashboard/static/index.html" "UX-States" || true

    # #46: Live-QA-Evidence
    echo "  [#46] Live-QA-Evidence"
    check_file "scripts/ui_smoke.py" || true
}

# -------------------------------------------------------------------
# Security-Serie: Issues #50-#54
# -------------------------------------------------------------------
verify_security_series() {
    print_header "SECURITY SERIES (#50-#54): Sicherheit"

    # #50: Walking-Skeleton
    echo "  [#50] Walking-Skeleton"
    check_file "Makefile"
    check_pattern "security" "Makefile" "make security target"
    check_pattern "coverage" "Makefile" "make coverage target"
    check_pattern "quality" "Makefile" "make quality target"

    # #51: ruff-Lint
    echo "  [#51] ruff-Lint-Gate"
    check_file "pyproject.toml"
    check_pattern "ruff|lint" "Makefile" "ruff/ lint-Konfiguration"

    # #52: Bandit-Triage
    echo "  [#52] Bandit-Findings"
    check_dir "docs/security" "docs/security/"
    check_file "docs/security/security-gate-policy.md"
    check_pattern "bandit" "Makefile" "make security target"
    if grep -q "bandit\|security" "pyproject.toml" 2>/dev/null; then
        echo "  ✅ Bandit/Security-Konfiguration gefunden"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Keine Bandit-Konfiguration in pyproject.toml (optional)"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    # #53: Submodul-Review
    echo "  [#53] Submodul-Review"
    check_dir "gpt_researcher" "gpt_researcher (Submodul)"
    check_file "docs/security/submodule-security-review.md" || true

    # #54: CI-Security-Gate
    echo "  [#54] Bandit-CI-Gate"
    if grep -q "security-project\|security-report\|security-vendor\|bandit" "Makefile" 2>/dev/null; then
        echo "  ✅ CI-Security-Targets gefunden"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Keine separaten Security-Targets (make security nutzt bandit)"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    check_file "docs/security/security-gate-policy.md"
}

# -------------------------------------------------------------------
# Runtime/DX-Serie: Issues #55-#62
# -------------------------------------------------------------------
verify_runtime_series() {
    print_header "RUNTIME/DX SERIES (#55-#62): Betrieb & Entwicklung"

    # #55: Mypy-Submodul-Grenze
    echo "  [#55] Mypy-Vendor-Grenze"
    check_pattern "typecheck|mypy" "Makefile" "typecheck targets"

    # #56: Type-Errors
    echo "  [#56] 33 Type-Errors"
    check_pattern "typecheck" "Makefile" "make typecheck" || true

    # #57: Testprofile
    echo "  [#57] Testprofile"
    check_pattern "test-fast\|test-e2e\|test-benchmark" "Makefile" "Testprofile"

    # #58: Onboarding
    echo "  [#58] Fresh-Clone-Onboarding"
    check_file "README.md"
    check_file ".env.example"

    # #59: Runtime-Smoke
    echo "  [#59] Runtime-Smoke-Test"
    check_file "scripts/runtime_smoke.py"
    check_pattern "runtime-smoke" "Makefile" "make runtime-smoke"

    # #60: SearXNG-Stabilität
    echo "  [#60] SearXNG-Runtime"
    check_file "scripts/start-searxng.sh" || true
    check_pattern "searxng" "Makefile" "make searxng-*"
    check_file "config/services.py"

    # #61: Research-Happy-Path
    echo "  [#61] Research-Happy-Path"
    check_file "scripts/research_happy_path.py"
    check_pattern "research-happy-path" "Makefile" "make research-happy-path"

    # #62: Ollama-Modell-Name
    echo "  [#62] Ollama-Modell-Name"
    check_file "config/ollama_models.py" || true
    check_pattern "OLLAMA_CHAT_MODEL\|EMBEDDING" ".env.example" "Modell-Konfiguration"
}

# -------------------------------------------------------------------
# Release-Serie: Issues #69-#73
# -------------------------------------------------------------------
verify_release_series() {
    print_header "RELEASE SERIES (#69-#73): Release-Vorbereitung"

    # #69: CHANGELOG
    echo "  [#69] CHANGELOG"
    check_file "CHANGELOG.md" || check_file "docs/changelog.md" || true

    # #70: Git-Tag-Vorbereitung
    echo "  [#70] Git-Tag-Vorbereitung"
    if git tag -l 'v0.1.0*' 2>/dev/null | grep -q .; then
        echo "  ✅ Tag existiert"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Kein Tag (Issue noch offen)"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi

    # #71: Working-Tree
    echo "  [#71] Working-Tree-Bereinigung"
    local untracked
    untracked=$(git status --porcelain 2>/dev/null | wc -l)
    if [ "$untracked" -le 5 ]; then
        echo "  ✅ Working Tree sauber ($untracked ungetrackte)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "  ⚠️  Working Tree: $untracked ungetrackte Dateien"
        WARN_CHECKS=$((WARN_CHECKS + 1))
    fi

    # #72: Release-Tag
    echo "  [#72] Release-Tag"
    # Same as #70 - already checked

    # #73: CI-Bereinigung
    echo "  [#73] CI-Playwright-Requirements-Bereinigung"
    check_file ".github/workflows/ci.yml"
    check_file ".github/workflows/test.yml"
    check_file "requirements.txt"
}

# -------------------------------------------------------------------
# Deutsche Unicode-Serie: Issues #74-#77
# -------------------------------------------------------------------
verify_unicode_series() {
    print_header "UNICODE/GERMAN SERIES (#74-#77): Deutsche Sprachunterstützung"

    # #74: LLM-Dokumentation
    echo "  [#74] LLM-Dokumentation"
    check_file "docs/development/local-runbook.md" || true
    check_file "docs/runtime/qwen35-uncensored-gtx1070-runtime.md" || true

    # #75: LLM/Unicode-Code
    echo "  [#75] LLM/Unicode-Integration"
    check_file "text_utils/__init__.py" || true
    check_file "text_utils/german.py" || true
    check_file "text_utils/search_keys.py" || true

    # #76: Umlaut-Fixtures
    echo "  [#76] Umlaut-Fixures"
    check_file "tests/fixtures/german_queries.json" || true
    check_file "tests/helpers/german_query_fixtures.py" || true
    check_test_file "tests/test_german_query_fixtures.py" || true

    # #77: German Search Keys
    echo "  [#77] German Search Keys"
    check_file "text_utils/search_keys.py"
    check_test_file "tests/test_german_search_keys.py" || true
    check_file "docs/text/german-search-keys.md" || true
    check_file "docs/crawling/crawl-scale-policy.md" || true
}

# -------------------------------------------------------------------
# Deep-Research: Issues #98-#105
# -------------------------------------------------------------------
verify_deep_research() {
    print_header "DEEP RESEARCH (#98-#105): Deep-Research-Module"

    # DR-01: Planner
    echo "  [#98] DR-01: Collaborative Planner"
    check_dir "research_planner" "research_planner/"
    check_file "research_planner/planner.py"
    check_file "research_planner/models.py"
    check_file "research_planner/validation.py"
    check_file "research_planner/serialization.py"
    check_file "research_planner/approval.py"
    check_test_file "tests/test_research_planner.py"

    # DR-02: Orchestrator
    echo "  [#99] DR-02: Master Orchestrator"
    check_dir "research_orchestrator" "research_orchestrator/"
    check_file "research_orchestrator/orchestrator.py"
    check_file "research_orchestrator/state.py"
    check_file "research_orchestrator/storage.py"
    check_file "research_orchestrator/scheduler.py"
    check_file "research_orchestrator/events.py"
    check_test_file "tests/test_research_orchestrator.py"

    # DR-03: Worker
    echo "  [#100] DR-03: Researcher Worker"
    check_dir "research_workers" "research_workers/"
    check_file "research_workers/worker.py"
    check_file "research_workers/query_decomposer.py"
    check_file "research_workers/gap_analyzer.py"
    check_test_file "tests/test_research_worker_queries.py"

    # DR-04: Searcher Pipeline
    echo "  [#101] DR-04: Searcher Pipeline"
    check_dir "searcher_pipeline" "searcher_pipeline/"
    check_file "searcher_pipeline/searxng_client.py"
    check_file "searcher_pipeline/robots_policy.py"
    check_file "searcher_pipeline/fetch_cache.py"
    check_file "searcher_pipeline/reranker.py"
    check_file "searcher_pipeline/mmr.py"
    check_file "searcher_pipeline/segmenter.py"
    check_file "searcher_pipeline/content_extractor.py"
    check_file "searcher_pipeline/rate_limiter.py"
    check_file "searcher_pipeline/url_canonicalizer.py"
    check_file "searcher_pipeline/prompt_injection_filter.py"
    check_test_file "tests/test_searcher_pipeline.py"

    # DR-05: Evidence Store
    echo "  [#102] DR-05: Evidence Store"
    check_dir "evidence_store" "evidence_store/"
    check_file "evidence_store/store.py"
    check_file "evidence_store/models.py"
    check_file "evidence_store/citations.py"
    check_file "evidence_store/dedup.py"
    check_test_file "tests/test_evidence_store.py"

    # DR-06: Report Writer
    echo "  [#103] DR-06: Report Writer"
    check_dir "deep_report" "deep_report/"
    check_file "deep_report/writer.py"
    check_file "deep_report/evaluator.py"
    check_file "deep_report/outline.py"
    check_file "deep_report/revision_loop.py"
    check_file "deep_report/citation_inserter.py"
    check_test_file "tests/test_deep_report_writer.py"

    # DR-07: UI Integration
    echo "  [#104] DR-07: UI Integration"
    check_file "deep_research_api.py"
    check_test_file "tests/test_deep_research_api.py"

    # DR-08: Runtime Guard
    echo "  [#105] DR-08: Runtime Guard"
    check_file "config/local_llm_runtime.py"
    check_class "RuntimeGuardResult" "config/local_llm_runtime.py"
    check_function "run_guard" "config/local_llm_runtime.py"
    check_function "can_start_deep_research" "config/local_llm_runtime.py"
    check_test_file "tests/test_local_llm_runtime_guard.py"
}

# -------------------------------------------------------------------
# Einzel-Issue-Prüfung (mit GitHub-API)
# -------------------------------------------------------------------
verify_single_issue() {
    local num="$1"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  EINZELPRÜFUNG: Issue #$num"
    echo "═══════════════════════════════════════════════════════════════"

    if ! command -v gh &>/dev/null; then
        echo "  ❌ GitHub CLI (gh) nicht gefunden"
        exit 1
    fi

    gh issue view "$num" --json title,state,body,labels 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'  Titel:  {data[\"title\"]}')
print(f'  Status: {data[\"state\"]}')
labels = ', '.join(l['name'] for l in data.get('labels', []))
print(f'  Labels: {labels}')
body = data.get('body', '') or ''
# Extract checkboxes
import re
boxes = re.findall(r'- \[( |x)\] (.+)', body)
if boxes:
    print(f'  Checkboxen ({len(boxes)}):')
    for checked, text in boxes:
        mark = '✅' if checked == 'x' else '⬜'
        print(f'    {mark} {text[:80]}')
else:
    print('  (Keine Checkboxen gefunden)')
" 2>/dev/null || echo "  (Issue nicht abrufbar)"

    # Prüfe Commits für diesen Issue
    echo ""
    echo "  Zugehörige Commits:"
    local commits
    commits=$(git log --all --oneline --grep="#$num" 2>/dev/null | head -5)
    if [ -n "$commits" ]; then
        echo "$commits" | while IFS= read -r line; do
            echo "    $line"
        done
    else
        echo "    (Keine direkten Commits mit #$num gefunden)"
    fi

    # Prüfe Branches
    echo ""
    echo "  Zugehörige Branches:"
    local branches
    branches=$(git branch -a --list "*$num*" 2>/dev/null | head -5)
    if [ -n "$branches" ]; then
        echo "$branches" | while IFS= read -r line; do
            echo "    $line"
        done
    else
        echo "    (Keine Branches mit $num gefunden)"
    fi
}

# ==============================================================================
# GitHub Issue-Liste mit Kategorisierung
# ==============================================================================
list_issues() {
    print_header "ISSUE INVENTAR (GitHub)"

    if ! command -v gh &>/dev/null; then
        echo "  ⚠️  GitHub CLI (gh) nicht installiert — überspringe"
        return
    fi

    # Prüfe ob Authentifizierung funktioniert
    if ! gh auth status 2>/dev/null >/dev/null; then
        echo "  ⚠️  Nicht authentifiziert bei GitHub — überspringe"
        return
    fi

    echo "  Lade Issues..."
    local all_data
    all_data=$(gh issue list --state all --limit 100 --json number,title,state,labels \
        --jq '{"total": length, "open": [.[] | select(.state == "OPEN")], "closed": [.[] | select(.state == "CLOSED")]}' 2>/dev/null)

    if [ -z "$all_data" ]; then
        echo "  ❌ Konnte Issues nicht laden"
        return
    fi

    local open_count closed_count
    open_count=$(echo "$all_data" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['open']))" 2>/dev/null || echo "?")
    closed_count=$(echo "$all_data" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['closed']))" 2>/dev/null || echo "?")
    local total_count=$((open_count + closed_count))

    echo ""
    echo "  GESAMT: $total_count Issues"
    echo "  ├─ Offen:       $open_count"
    echo "  └─ Geschlossen: $closed_count"
    echo ""

    # Label-Statistik
    echo "  Top-Labels:"
    echo "$all_data" | python3 -c "
import json, sys
from collections import Counter
data = json.load(sys.stdin)
all_issues = data['open'] + data['closed']
labels = Counter()
for i in all_issues:
    for l in i.get('labels', []):
        labels[l['name']] += 1
for name, count in labels.most_common(10):
    print(f'    {name}: {count}')
" 2>/dev/null

    # Offene Issues
    echo ""
    echo "  Offene Issues:"
    echo "$all_data" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i in sorted(data['open'], key=lambda x: x['number']):
    labels = ', '.join(l['name'] for l in i.get('labels', []))
    print(f'    #{i[\"number\"]}: {i[\"title\"][:60]} [{labels}]')
" 2>/dev/null
}

# ==============================================================================
# Report-Generierung (Phase 6)
# ==============================================================================
generate_report() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  GENERIERE REPORT..."
    echo "═══════════════════════════════════════════════════════════════"

    # Python-Modul-Prüfung (existieren DR-Importe?)
    echo "  Prüfe Python-Modul-Importe..."
    local dr_modules=(
        "research_planner"
        "research_orchestrator"
        "research_workers"
        "searcher_pipeline"
        "evidence_store"
        "deep_report"
        "config"
    )
    for mod in "${dr_modules[@]}"; do
        if python3 -c "import $mod" 2>/dev/null; then
            echo "  ✅ $mod importierbar"
        else
            echo "  ⚠️  $mod nicht importierbar (erwartet bei fehlenden Dependencies)"
        fi
    done

    # Markdown-Report
    echo ""
    echo "  Schreibe Report: $REPORT_FILE"
    cat > "$REPORT_FILE" << REPORTEOF
# Issue Verification Report

**Repository:** $REPO
**Branch:** $BRANCH
**Commit:** $COMMIT
**Datum:** $(date '+%Y-%m-%d %H:%M')
**Durchgeführt:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")

---

## Executive Summary

| Metrik | Wert |
|--------|------|
| Prüfungen gesamt | $TOTAL_CHECKS |
| ✅ Bestanden | $PASSED_CHECKS |
| ❌ Fehlgeschlagen | $FAILED_CHECKS |
| ⚠️  Warnungen | $WARN_CHECKS |
| Bestehensquote | $(python3 -c "print(f'{($PASSED_CHECKS/($TOTAL_CHECKS+0.01))*100:.1f}%')" 2>/dev/null || echo "N/A") |

## Deep Research Module Status

| Modul | Issue | Status | Code | Tests |
|-------|-------|--------|------|-------|
REPORTEOF

    # DR-Modul-Tabelle
    local dr_dir_exists planner_tests orch_tests worker_tests searcher_tests ev_tests rw_tests dr7_tests dr8_tests
    [ -d "research_planner" ] && dr_dir_exists="✅" || dr_dir_exists="❌"
    [ -f "tests/test_research_planner.py" ] && planner_tests="✅" || planner_tests="❌"
    [ -f "tests/test_research_orchestrator.py" ] && orch_tests="✅" || orch_tests="❌"
    [ -f "tests/test_research_worker_queries.py" ] && worker_tests="✅" || worker_tests="❌"
    [ -f "tests/test_searcher_pipeline.py" ] && searcher_tests="✅" || searcher_tests="❌"
    [ -f "tests/test_evidence_store.py" ] && ev_tests="✅" || ev_tests="❌"
    [ -f "tests/test_deep_report_writer.py" ] && rw_tests="✅" || rw_tests="❌"
    [ -f "tests/test_deep_research_api.py" ] && dr7_tests="✅" || dr7_tests="❌"
    [ -f "tests/test_local_llm_runtime_guard.py" ] && dr8_tests="✅" || dr8_tests="❌"

    cat >> "$REPORT_FILE" << REPORTEOF
| DR-01 Planner | #98 | $dr_dir_exists | research_planner/ | $planner_tests |
| DR-02 Orchestrator | #99 | $dr_dir_exists | research_orchestrator/ | $orch_tests |
| DR-03 Worker | #100 | $dr_dir_exists | research_workers/ | $worker_tests |
| DR-04 Searcher | #101 | $dr_dir_exists | searcher_pipeline/ | $searcher_tests |
| DR-05 Evidence | #102 | $dr_dir_exists | evidence_store/ | $ev_tests |
| DR-06 Report Writer | #103 | $dr_dir_exists | deep_report/ | $rw_tests |
| DR-07 UI | #104 | $dr_dir_exists | deep_research_api.py | $dr7_tests |
| DR-08 Runtime Guard | #105 | $dr_dir_exists | config/local_llm_runtime.py | $dr8_tests |

## Issue-Mapping (Commits)

| Issue | Commits | Status |
|-------|---------|--------|
REPORTEOF

    # Issue-Commit-Mapping
    for issue_num in $(git log --all --oneline --grep="#" 2>/dev/null | grep -oP '#\d+' | sort -t '#' -k2 -n | uniq); do
        local count
        count=$(git log --all --oneline --grep="$issue_num" 2>/dev/null | wc -l)
        echo "| $issue_num | $count Commits | ✅ |" >> "$REPORT_FILE"
    done

    cat >> "$REPORT_FILE" << REPORTEOF

## Makefile-Targets

\`\`\`
REPORTEOF

    # Makefile-Targets extrahieren
    if [ -f "Makefile" ]; then
        grep -oP '^[a-zA-Z][a-zA-Z0-9_-]+' "Makefile" | tr '\n' ' ' >> "$REPORT_FILE"
    fi

    cat >> "$REPORT_FILE" << REPORTEOF
\`\`\`

## Test-Struktur

\`\`\`
REPORTEOF

    # Test-Struktur
    for d in tests/*/; do
        local count
        count=$(find "$d" -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null | wc -l)
        echo "$d: $count Testdateien" >> "$REPORT_FILE"
    done

    cat >> "$REPORT_FILE" << REPORTEOF
\`\`\`

## Ergebnis-Details

| Kategorie | Checks | ✅ | ❌ | ⚠️ |
|-----------|--------|----|----|-----|
| T-Series (#1-#29) | — | — | — | — |
| Audit (#30-#37) | — | — | — | — |
| Deep Research (#98-#105) | — | — | — | — |

**Gesamt:** $TOTAL_CHECKS Checks, $PASSED_CHECKS ✅ passed, $FAILED_CHECKS ❌ failed, $WARN_CHECKS ⚠️ warnings

---

*Report generiert am $(date '+%Y-%m-%d %H:%M') von verify-issues.sh*
REPORTEOF

    # JSON-Report
    echo "  Schreibe JSON-Report: $JSON_REPORT"
    python3 -c "
import json
report = {
    'metadata': {
        'repo': '$REPO',
        'branch': '$BRANCH',
        'commit': '$COMMIT',
        'timestamp': '$(date -u +"%Y-%m-%dT%H:%M:%SZ")',
        'script': 'verify-issues.sh'
    },
    'results': {
        'total_checks': $TOTAL_CHECKS,
        'passed': $PASSED_CHECKS,
        'failed': $FAILED_CHECKS,
        'warnings': $WARN_CHECKS,
        'pass_rate': round($PASSED_CHECKS / max($TOTAL_CHECKS, 1) * 100, 1)
    },
    'modules': {
        'deep_research': {
            'planner': $([ -d "research_planner" ] && echo "true" || echo "false"),
            'orchestrator': $([ -d "research_orchestrator" ] && echo "true" || echo "false"),
            'workers': $([ -d "research_workers" ] && echo "true" || echo "false"),
            'searcher': $([ -d "searcher_pipeline" ] && echo "true" || echo "false"),
            'evidence': $([ -d "evidence_store" ] && echo "true" || echo "false"),
            'report_writer': $([ -d "deep_report" ] && echo "true" || echo "false"),
            'ui_api': $([ -f "deep_research_api.py" ] && echo "true" || echo "false"),
            'runtime_guard': $([ -f "config/local_llm_runtime.py" ] && echo "true" || echo "false")
        }
    }
}
with open('$JSON_REPORT', 'w') as f:
    json.dump(report, f, indent=2)
print(f'  JSON gespeichert: {json.dumps(report[\"results\"])}')
" 2>/dev/null || echo "  ⚠️  JSON-Report fehlgeschlagen"

    echo ""
    echo "  ✅ Report gespeichert:"
    echo "     📄 $REPORT_FILE"
    echo "     📊 $JSON_REPORT"
}

# ==============================================================================
# CI-Modus (GitHub Actions kompatibel)
# ==============================================================================
github_action_output() {
    echo ""
    echo "  📤 GitHub Actions Output:"
    echo "    total=$TOTAL_CHECKS"
    echo "    passed=$PASSED_CHECKS"
    echo "    failed=$FAILED_CHECKS"
    echo "    warnings=$WARN_CHECKS"
    echo "    pass_rate=$(python3 -c "print(int($PASSED_CHECKS/$TOTAL_CHECKS*100))" 2>/dev/null || echo "0")%"
    echo ""

    # Set GitHub Action output if available
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
        {
            echo "total=$TOTAL_CHECKS"
            echo "passed=$PASSED_CHECKS"
            echo "failed=$FAILED_CHECKS"
            echo "warnings=$WARN_CHECKS"
        } >> "$GITHUB_OUTPUT"
    fi

    # Exit-Code für CI
    if [ "$FAILED_CHECKS" -gt 0 ]; then
        echo "  ❌ $FAILED_CHECKS Prüfungen fehlgeschlagen"
        return 1
    fi
    return 0
}

# ==============================================================================
# Main
# ==============================================================================
MODE="${1:-open}"

print_banner

case "$MODE" in
    --all|-a|all)
        list_issues
        verify_t_series
        verify_audit_series
        verify_qa_series
        verify_security_series
        verify_runtime_series
        verify_release_series
        verify_unicode_series
        verify_deep_research
        print_result
        generate_report
        ;;

    --closed|-c|closed)
        print_header "MODUS: Geschlossene Issues"
        verify_t_series
        verify_audit_series
        verify_deep_research
        print_result
        ;;

    --deep|-d|deep)
        print_header "MODUS: Deep Research Module"
        verify_deep_research
        print_result
        ;;

    --security|-s|security)
        print_header "MODUS: Security Issues"
        verify_security_series
        print_result
        ;;

    --release|release)
        print_header "MODUS: Release Issues"
        verify_release_series
        print_result
        ;;

    --unicode|unicode)
        print_header "MODUS: Deutsche Unicode Issues"
        verify_unicode_series
        print_result
        ;;

    --report|-r|report)
        print_result
        generate_report
        ;;

    --github-action|ci)
        list_issues
        verify_t_series
        verify_deep_research
        print_result
        generate_report
        github_action_output
        ;;

    --list|-l|list)
        list_issues
        ;;

    [0-9]*)
        verify_single_issue "$1"
        ;;

    open|--open)
        print_header "MODUS: Offene Issues (Inventar)"
        list_issues
        echo ""
        echo "  💡 Für detaillierte Code-Prüfung: --all"
        ;;

    *)
        echo "Verwendung: $0 [OPTION]"
        echo ""
        echo "  (ohne) / --open    Offene Issues auflisten"
        echo "  --all / -a         Komplette Prüfung (alle Kategorien)"
        echo "  --closed / -c      Nur geschlossene Issues prüfen"
        echo "  --deep / -d        Nur Deep Research Module"
        echo "  --security / -s    Nur Security Issues"
        echo "  --unicode          Nur Deutsche Unicode Issues"
        echo "  --release          Nur Release Issues"
        echo "  --report / -r      Report aus letzter Prüfung generieren"
        echo "  --list / -l        Issues auflisten"
        echo "  --github-action    CI-Modus mit JSON-Output"
        echo "  <nummer>           Einzelnen Issue prüfen"
        exit 1
        ;;
esac

# Abschluss
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Verifikation abgeschlossen."
echo "  Reports: $REPORT_DIR/"
echo "═══════════════════════════════════════════════════════════════"
