#!/usr/bin/env bash
# =============================================================================
# Issue Verifikations-Script
# Prüft GitHub Issues gegen tatsächlichen Code
# =============================================================================
# Verwendung:
#   ./scripts/verify-issues.sh              # Alle offenen Issues prüfen
#   ./scripts/verify-issues.sh 42           # Einzelnen Issue prüfen
#   ./scripts/verify-issues.sh --closed     # Nur geschlossene Issues prüfen
#   ./scripts/verify-issues.sh --report     # Nur Report generieren
# =============================================================================

set -euo pipefail

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || echo "local")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
REPORT_DIR="reports/issue-verification"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$REPORT_DIR"

echo "╔════════════════════════════════════════════════════╗"
echo "║   Researcher Issue Verifikation                   ║"
echo "║   Repo: $REPO"
echo "║   Branch: $BRANCH"
echo "║   Commit: $COMMIT"
echo "║   Datum: $(date '+%Y-%m-%d %H:%M')"
echo "╚════════════════════════════════════════════════════╝"

# =============================================================================
# Helper: Prüfe ob Datei existiert
# =============================================================================
check_file() {
    local file="$1"
    local label="${2:-$file}"
    if [ -f "$file" ]; then
        local lines
        lines=$(wc -l < "$file")
        echo "  ✅ $label ($lines Zeilen)"
        return 0
    else
        echo "  ❌ $label (FEHLT)"
        return 1
    fi
}

# =============================================================================
# Helper: Prüfe ob Pattern in Datei existiert
# =============================================================================
check_pattern() {
    local pattern="$1"
    local file="$2"
    local label="${3:-$pattern}"
    if [ -f "$file" ] && grep -q "$pattern" "$file" 2>/dev/null; then
        local count
        count=$(grep -c "$pattern" "$file" 2>/dev/null || echo "0")
        echo "  ✅ $label ($count Treffer)"
        return 0
    else
        echo "  ❌ $label (Pattern nicht gefunden)"
        return 1
    fi
}

# =============================================================================
# Helper: Prüfe Test-Funktionen
# =============================================================================
check_tests() {
    local pattern="$1"
    local dir="${2:-tests}"
    local label="${3:-Tests für $pattern}"
    local count
    count=$(grep -rn "def test_" "$dir" --include="*.py" 2>/dev/null | grep -i "$pattern" | wc -l || echo "0")
    if [ "$count" -gt 0 ]; then
        echo "  ✅ $label ($count Tests)"
        return 0
    else
        echo "  ⚠️  $label (Keine Tests gefunden)"
        return 1
    fi
}

# =============================================================================
# Issue-Prüfung nach Kategorie
# =============================================================================
verify_issue_001_029() {
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "  ISSUES #1-#29: Vibe-Coding Basis"
    echo "════════════════════════════════════════════════════"
    local passed=0
    local failed=0

    # #1: Repository & Basis
    echo "  [#1] Repository & Basis-Umgebung"
    check_file ".env.example" && ((passed++)) || ((failed++))
    check_file "requirements.txt" && ((passed++)) || ((failed++))
    check_file ".gitignore" && ((passed++)) || ((failed++))

    # #2: Ollama
    echo "  [#2] Ollama + Qwen3"
    check_file "serve_qwen3.5_uncensored.sh" && ((passed++)) || ((failed++))

    # #3: SearXNG
    echo "  [#3] SearXNG Docker"
    check_file "searxng/settings.yml" "searxng/settings.yml" && ((passed++)) || ((failed++))

    # #4: GPT Researcher
    echo "  [#4] GPT Researcher Fork"
    check_file "gpt_researcher/main.py" "gpt_researcher/main.py" && ((passed++)) || ((failed++))

    # #5: Darknet-Crawler
    echo "  [#5] Darknet-Crawler"
    check_file "crawlers/darknet_crawler.py" && ((passed++)) || ((failed++))
    check_pattern "SOCKS5\|socks5" "crawlers/darknet_crawler.py" "Tor SOCKS5" && ((passed++)) || ((failed++))

    # #6: Whoosh-Index
    echo "  [#6] Whoosh-Index + DarknetRetriever"
    check_file "darknet_search/index.py" && ((passed++)) || ((failed++))
    check_file "darknet_search/retriever.py" && ((passed++)) || ((failed++))

    # #7: CompositeRetriever
    echo "  [#7] CompositeRetriever"
    check_file "search/composite.py" && ((passed++)) || ((failed++))

    # #8: ChromaDB
    echo "  [#8] ChromaDB + Embeddings"
    check_file "vectordb/store.py" && ((passed++)) || ((failed++))

    # #9: VRAM
    echo "  [#9] VRAM-Optimierungen"
    check_file "dashboard/gpu_monitor.py" && ((passed++)) || ((failed++))

    # #10: Integrationstests
    echo "  [#10] Integrationstests"
    check_tests "composite\|e2e\|integration" "tests" "Integration/E2E-Tests" && ((passed++)) || ((failed++))

    # #11: Dokumentation
    echo "  [#11] Dokumentation"
    check_file "README.md" && ((passed++)) || ((failed++))
    check_file "docs/troubleshooting.md" && ((passed++)) || ((failed++))

    # #12-13: Onion Discovery
    echo "  [#12-13] Onion Discovery Engine"
    check_file "onion_discovery/engine.py" && ((passed++)) || ((failed++))
    check_file "onion_discovery/seed_queue.py" && ((passed++)) || ((failed++))

    # #14: Architecture Review
    echo "  [#14] Architecture Review"
    check_file "docs/architecture.md" && ((passed++)) || ((failed++))

    # #16: MCP-Tools
    echo "  [#16] MCP-Tools"
    check_file "mcp_tools/web_fetch.py" && ((passed++)) || ((failed++))
    check_file "mcp_tools/evidence_store.py" && ((passed++)) || ((failed++))
    check_file "mcp_tools/human_review.py" && ((passed++)) || ((failed++))

    # #17: GPU Dashboard
    echo "  [#17] GPU/VRAM Dashboard"
    check_file "dashboard/server.py" && ((passed++)) || ((failed++))
    check_pattern "gpu\|SSE\|sse\|stream" "dashboard/server.py" "GPU SSE Stream" && ((passed++)) || ((failed++))

    # #19: SSRF
    echo "  [#19] SSRF-Schutz"
    check_pattern "_PRIVATE_NETWORKS\|_validate_url_target" "mcp_tools/web_fetch.py" "SSRF Protection" && ((passed++)) || ((failed++))

    # #20: Human-Review-Gate
    echo "  [#20] Human-Review-Gate"
    if grep -q "approve\|reject" "mcp_tools/human_review.py" && ! grep -q "def approve\|def reject" "mcp_tools/human_review.py"; then
        echo "  ✅ Approve/Reject aus MCP entfernt"
        ((passed++))
    else
        echo "  ❌ Approve/Reject Schutz nicht verifiziert"
        ((failed++))
    fi

    # #21: Path Traversal
    echo "  [#21] Path-Traversal-Schutz"
    check_pattern "realpath\|\.\." "dashboard/server.py" "Path Traversal Schutz" && ((passed++)) || ((failed++))

    # #30-37: Audit Fixes
    echo "  [#30-37] Codebase Audit Fixes"
    check_pattern "sha256" "darknet_search/index.py" "SHA256 statt hash() [#30]" && ((passed++)) || ((failed++))
    check_pattern "sha256" "onion_discovery/engine.py" "SHA256 in Onion [#36]" && ((passed++)) || ((failed++))

    echo ""
    echo "  Ergebnis: $passed Checks passed, $failed Checks failed"
    return $failed
}

verify_issue_079_096() {
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "  ISSUES #79-#96: QA/Test/Integration"
    echo "════════════════════════════════════════════════════"
    local passed=0
    local failed=0

    # #79: SSRF Tests
    echo "  [#79] SSRF Regression Tests"
    check_tests "ssrf\|SSRF\|web_fetch\|_validate_url" "tests" "SSRF Tests" && ((passed++)) || ((failed++))
    check_file "tests/security/test_ssrf_protection.py" && ((passed++)) || ((failed++))

    # #80: Onion Pipeline Tests
    echo "  [#80] Onion Discovery Pipeline Tests"
    check_file "tests/integration/test_onion_pipeline.py" && ((passed++)) || ((failed++))
    check_tests "onion_pipeline\|state_machine\|content_policy" "tests" "Onion Pipeline Tests" && ((passed++)) || ((failed++))

    # #81: Chaos Tests
    echo "  [#81] Chaos/Resilience Tests"
    check_file "tests/chaos/test_composite_resilience.py" && ((passed++)) || ((failed++))
    check_file "tests/chaos/test_external_service_resilience.py" && ((passed++)) || ((failed++))

    # #82: E2E Tests
    echo "  [#82] E2E Playwright Tests"
    check_file "tests/e2e/test_full_research_flow.py" && ((passed++)) || ((failed++))
    check_file "tests/playwright/test_dashboard_visual_regression.py" && ((passed++)) || ((failed++))

    # #87: Darknet Crawler Coverage
    echo "  [#87] Darknet-Crawler Tests"
    check_file "tests/test_crawlers.py" && ((passed++)) || ((failed++))
    check_tests "crawler\|login\|session" "tests/test_crawlers.py" "Crawler Tests" && ((passed++)) || ((failed++))

    # #88: MCP Claim Coverage
    echo "  [#88] MCP Claim Module Tests"
    check_file "tests/test_claim_validator.py" && ((passed++)) || ((failed++))
    check_tests "claim" "tests" "Claim Tests" && ((passed++)) || ((failed++))

    # #91: UI Local Readiness
    echo "  [#91] UI Local Readiness"
    check_file "docs/development/ui-local-readiness.md" && ((passed++)) || ((failed++))

    # #93: GPT Researcher Integration
    echo "  [#93] GPT-Researcher Frontend"
    check_file "gpt_researcher/main.py" && ((passed++)) || ((failed++))

    # #94: UI Startup Verify
    echo "  [#94] UI Startup Verify"
    check_file "scripts/ui_smoke.py" && ((passed++)) || ((failed++))

    echo ""
    echo "  Ergebnis: $passed Checks passed, $failed Checks failed"
    return $failed
}

verify_issue_open() {
    local num="$1"
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "  ISSUE #$num: (Einzelprüfung)"
    echo "════════════════════════════════════════════════════"

    gh issue view "$num" --json title,state,body 2>/dev/null | jq -r '"  Titel: \(.title)", "  Status: \(.state)"' 2>/dev/null || echo "  (Issue nicht abrufbar)"

    echo ""
    echo "  Manuelle Prüfung erforderlich — siehe Report für Details."
}

generate_report_summary() {
    local report_file="$REPORT_DIR/verify-report-$TIMESTAMP.md"

    cat > "$report_file" << EOF
# Issue Verification Report
**Repository:** $REPO
**Branch:** $BRANCH
**Commit:** $COMMIT
**Date:** $(date '+%Y-%m-%d %H:%M')

## Summary
- Open Issues: $(gh issue list --state open --json number --jq 'length' 2>/dev/null || echo "?")
- Closed Issues: $(gh issue list --state closed --json number --jq 'length' 2>/dev/null || echo "?")
- Verificaton Date: $TIMESTAMP

## Files Checked
EOF

    # Add list of key files
    for f in .env.example requirements.txt crawlers/darknet_crawler.py search/composite.py \
             dashboard/server.py dashboard/gpu_monitor.py mcp_tools/web_fetch.py \
             onion_discovery/engine.py deep_research_api.py scripts/runtime_smoke.py; do
        if [ -f "$f" ]; then
            echo "- ✅ $f ($(wc -l < "$f") lines)" >> "$report_file"
        else
            echo "- ❌ $f (MISSING)" >> "$report_file"
        fi
    done

    echo ""
    echo "Report saved to: $report_file"
}

# =============================================================================
# Main
# =============================================================================
MODE="${1:-open}"

case "$MODE" in
    --closed|-c)
        echo "Prüfe geschlossene Issues..."
        verify_issue_001_029
        verify_issue_079_096
        ;;
    --report|-r)
        echo "Generiere Report..."
        generate_report_summary
        ;;
    --all|-a)
        echo "Prüfe alle Issues..."
        verify_issue_001_029
        verify_issue_079_096
        generate_report_summary
        ;;
    [0-9]*)
        verify_issue_open "$1"
        ;;
    *)
        echo "Verwendung: $0 [--all|--closed|--report|<issue-nummer>]"
        echo ""
        echo "  (ohne Argument)  Prüfe alle offenen Issues"
        echo "  --all            Prüfe alle Issues"
        echo "  --closed         Prüfe geschlossene Issues"
        echo "  --report         Nur Report generieren"
        echo "  <nummer>         Einzelnen Issue prüfen"
        exit 1
        ;;
esac
