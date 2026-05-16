#!/bin/bash
# =============================================================================
# run-all-tests.sh — Vollständige Researcher Test-Suite
# =============================================================================
# Führt alle Testebenen aus:
#   1. Statische Analyse (ruff, mypy, bandit)
#   2. Unit + Integration (pytest)
#   3. Coverage-Report
#   4. Playwright-Visual-Tests (optional)
#
# Nutzung:
#   ./scripts/run-all-tests.sh              # Vollständig
#   ./scripts/run-all-tests.sh --quick      # Nur pytest
#   ./scripts/run-all-tests.sh --ci         # Für CI (ohne Playwright)
#   ./scripts/run-all-tests.sh --coverage   # pytest + Coverage
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; FAILED=1; }
info() { echo -e "  ${YELLOW}→${NC} $1"; }

run_step() {
    local name="$1"
    shift
    echo ""
    echo "=== $name ==="
    echo ""
    if "$@" 2>&1; then
        pass "$name"
    else
        fail "$name (Exit: $?)"
    fi
}

cd "$SCRIPT_DIR"

case "${1:-}" in
    --quick|-q)
        run_step "pytest" python3 -m pytest tests/ -v --tb=short
        ;;
    --ci)
        run_step "ruff"     python3 -m ruff check . --line-length=88 --exit-zero
        run_step "pytest"   python3 -m pytest tests/ -v --tb=short
        run_step "coverage" python3 -m pytest tests/ --cov --cov-report=term
        ;;
    --coverage|-c)
        run_step "pytest + Coverage" \
            python3 -m pytest tests/ -v --cov --cov-report=term \
                --cov-report=html --cov-report=xml
        info "HTML-Report: coverage_html/index.html"
        info "XML-Report:  coverage.xml"
        ;;
    --help|-h)
        echo "run-all-tests.sh — Vollständige Testsuite"
        echo ""
        echo "  ./scripts/run-all-tests.sh               Alles"
        echo "  ./scripts/run-all-tests.sh --quick       Nur pytest"
        echo "  ./scripts/run-all-tests.sh --ci          CI-Modus"
        echo "  ./scripts/run-all-tests.sh --coverage    Mit Coverage"
        echo ""
        exit 0
        ;;
    *)
        # Vollständiger Durchlauf
        run_step "ruff"     python3 -m ruff check . --line-length=88 --exit-zero
        run_step "mypy"    python3 -m mypy . --ignore-missing-imports --no-strict-optional || true
        run_step "security" python3 -m bandit -r . --skip B101,B311,B404,B603 --quiet || true
        run_step "pytest"  python3 -m pytest tests/ -v
        run_step "coverage" python3 -m pytest tests/ --cov --cov-report=term --cov-report=html --cov-report=xml
        info "HTML-Report: coverage_html/index.html"
        ;;
esac

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo -e "  ${GREEN}✅ ALLE TESTS BESTANDEN${NC}"
else
    echo -e "  ${RED}❌ ES GAB FEHLER${NC}"
fi
echo ""

exit "$FAILED"
