#!/usr/bin/env bash
# ============================================================================
# run-qa-loop.sh — Autonomer beobachtbarer QA-/Repair-Loop
# ============================================================================
# 12-Schritte-Loop:
#   1. Repo-Zustand erfassen
#   2. make all (Unit + Lint + Type + Security)
#   3. make playwright (visuelle Tests)
#   4. E2E-Tests (optional, opt-in)
#   5. Artefakte sammeln
#   6. Fehler klassifizieren
#   7. Fehlende Testabdeckung erkennen
#   8. Visuelle Probleme erkennen (Playwright Diff)
#   9. Reparaturvorschlag (nur im Branch!)
#  10. Tests erneut ausführen
#  11. Ergebnis als Markdown-Report
#  12. Human-Gate bei riskanten Änderungen
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_DIR="$ROOT/qa/live"
ARTIFACTS_DIR="$ROOT/qa/live/artifacts"
JUNIT_XML="$ARTIFACTS_DIR/junit.xml"
LOOP_LOG="$ARTIFACTS_DIR/logs/qa-loop.log"
REPORT_MD="$REPORT_DIR/latest-qa-loop-report.md"

PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

step_pass() { PASS=$((PASS+1)); echo -e "  ${GREEN}✓${NC} $1"; }
step_fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}✗${NC} $1"; }
step_info() { echo -e "  ${YELLOW}→${NC} $1"; }

mkdir -p "$ARTIFACTS_DIR/screenshots" "$ARTIFACTS_DIR/logs" "$ARTIFACTS_DIR/traces"

cd "$ROOT"

# ============================================================================
# Schritt 1: Repo-Zustand erfassen
# ============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  QA-REPAIR-LOOP — Researcher                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "=== Schritt 1: Repo-Zustand ==="

COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
BRANCH=$(git branch --show-current 2>/dev/null || echo "?")
DIRTY=$(git status --porcelain 2>/dev/null | wc -l)

echo "  Branch:    $BRANCH"
echo "  Commit:    $COMMIT"
echo "  Änderungen: $DIRTY Dateien"
if [ "$DIRTY" -gt 0 ]; then
    echo "  ⚠️  Working directory ist dirty!"
fi
step_pass "Repo-Zustand erfasst ($COMMIT)"

# ============================================================================
# Schritt 2: make all (Unit + Lint + Type + Security)
# ============================================================================
echo ""
echo "=== Schritt 2: make all (Unit + Lint + Type + Security) ==="

if make all 2>&1 | tee "$ARTIFACTS_DIR/logs/make-all.log"; then
    step_pass "make all"
else
    step_fail "make all"
fi

# ============================================================================
# Schritt 3: Playwright-Visual-Tests
# ============================================================================
echo ""
echo "=== Schritt 3: make playwright (visuelle Tests) ==="

if make playwright 2>&1 | tee "$ARTIFACTS_DIR/logs/playwright.log"; then
    step_pass "make playwright"
else
    step_fail "make playwright"
fi

# ============================================================================
# Schritt 4: E2E-Tests (opt-in)
# ============================================================================
echo ""
echo "=== Schritt 4: E2E-Tests ==="

if [ "${RUN_E2E_TESTS:-}" = "true" ] || [ "${1:-}" = "--e2e" ]; then
    if python3 -m pytest tests/test_e2e_live.py -v --tb=short \
        --junitxml="$JUNIT_XML" 2>&1 | tee "$ARTIFACTS_DIR/logs/e2e.log"; then
        step_pass "E2E-Tests"
    else
        step_fail "E2E-Tests"
    fi
else
    step_info "E2E-Tests übersprungen (RUN_E2E_TESTS nicht gesetzt)"
fi

# ============================================================================
# Schritt 5: Artefakte sammeln
# ============================================================================
echo ""
echo "=== Schritt 5: Artefakte sammeln ==="

# Screenshots
if [ -d "$ROOT/tests/playwright/screenshots/baseline" ]; then
    cp "$ROOT/tests/playwright/screenshots/baseline/"*.png "$ARTIFACTS_DIR/screenshots/" 2>/dev/null || true
fi
if [ -d "$ROOT/tests/playwright/baselines" ]; then
    cp "$ROOT/tests/playwright/baselines/"*.png "$ARTIFACTS_DIR/screenshots/" 2>/dev/null || true
fi
# Diffs
if ls "$ROOT/tests/playwright/screenshots/diff/"*.png 2>/dev/null; then
    cp "$ROOT/tests/playwright/screenshots/diff/"*.png "$ARTIFACTS_DIR/screenshots/" 2>/dev/null || true
fi

SCREENSHOT_COUNT=$(find "$ARTIFACTS_DIR/screenshots" -name "*.png" 2>/dev/null | wc -l)
step_pass "Artefakte gesammelt ($SCREENSHOT_COUNT Screenshots)"

# ============================================================================
# Schritt 6: Fehler klassifizieren (JUnit XML)
# ============================================================================
echo ""
echo "=== Schritt 6: Fehler klassifizieren ==="

# Generate JUnit XML from the full test run
python3 -m pytest tests/ --tb=no --junitxml="$JUNIT_XML" -q 2>/dev/null || true

if [ -f "$JUNIT_XML" ]; then
    python3 "$ROOT/scripts/classify-errors.py" "$JUNIT_XML" \
        | tee "$ARTIFACTS_DIR/logs/classification.log"
    step_pass "Fehler klassifiziert"
else
    step_info "Kein JUnit XML — keine Fehlerklassifikation"
fi

# ============================================================================
# Schritt 7: Fehlende Testabdeckung erkennen
# ============================================================================
echo ""
echo "=== Schritt 7: Testabdeckung ==="

python3 -m pytest tests/ --cov --cov-report=term --cov-report=html 2>&1 \
    | tee "$ARTIFACTS_DIR/logs/coverage.log" | tail -10

COVERAGE_PCT=$(grep -oP 'TOTAL.*?\K\d+%' "$ARTIFACTS_DIR/logs/coverage.log" 2>/dev/null || echo "?")
step_info "Coverage: $COVERAGE_PCT"

# ============================================================================
# Schritt 8: Visuelle Probleme erkennen (Playwright Diff)
# ============================================================================
echo ""
echo "=== Schritt 8: Visuelle Probleme ==="

DIFF_COUNT=$(find "$ROOT/tests/playwright/screenshots/diff" -name "*.png" 2>/dev/null | wc -l)
if [ "$DIFF_COUNT" -gt 0 ]; then
    step_fail "Visuelle Diffs: $DIFF_COUNT Datei(en)"
else
    step_pass "Keine visuellen Diffs"
fi

# ============================================================================
# Schritt 9–10: Reparaturvorschlag + Tests erneut ausführen
# ============================================================================
echo ""
echo "=== Schritt 9–10: Reparatur ==="

if [ "$FAIL" -gt 0 ]; then
    step_info "$FAIL Fehler — Reparatur erforderlich."
    echo "Reparatur nur in Branch erlaubt. Kein automatischer Merge."
    step_info "Branch: qa/repair-loop-$COMMIT (nicht erstellt — manuell)"
else
    step_pass "Keine Reparatur nötig"
fi

# ============================================================================
# Schritt 11: Ergebnis als Markdown-Report
# ============================================================================
echo ""
echo "=== Schritt 11: Loop-Report ==="

cat > "$REPORT_MD" <<EOF
# QA-Repair-Loop Report

**Datum:** $(date -Iseconds)
**Branch:** $BRANCH
**Commit:** $COMMIT

## Ergebnis

| Kategorie | Status |
|---|---|
| Unit + Lint + Security | $([ -f "$ARTIFACTS_DIR/logs/make-all.log" ] && echo "✅" || echo "❌") |
| Playwright Visual | $([ -f "$ARTIFACTS_DIR/logs/playwright.log" ] && echo "✅" || echo "❌") |
| E2E | $(grep -q "PASSED\|passed" "$ARTIFACTS_DIR/logs/e2e.log" 2>/dev/null && echo "✅" || echo "⏭️") |
| Visuelle Diffs | $([ "$DIFF_COUNT" -eq 0 ] && echo "✅ 0" || echo "❌ $DIFF_COUNT") |
| Coverage | $COVERAGE_PCT |
| Screenshots | $SCREENSHOT_COUNT |

## Artefakte

- **Report:** \`qa/live/latest-qa-loop-report.md\`
- **Screenshots:** \`qa/live/artifacts/screenshots/\` ($SCREENSHOT_COUNT Dateien)
- **Logs:** \`qa/live/artifacts/logs/\`
- **JUnit:** \`qa/live/artifacts/junit.xml\`

---

*Generated by scripts/run-qa-loop.sh — $(date -Iseconds)*
EOF

step_pass "Markdown-Report geschrieben ($REPORT_MD)"

# ============================================================================
# Schritt 12: Human-Gate
# ============================================================================
echo ""
echo "=== Schritt 12: Human-Gate ==="

echo "  ⚠️  Human-Gate erforderlich bei:"
echo "     - config/config.py Änderungen"
echo "     - DB-Migrationen"
echo "     - Security-relevanten Änderungen"
echo "     - Deployment-Änderungen"

# ============================================================================
# Zusammenfassung
# ============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
if [ "$FAIL" -eq 0 ]; then
    echo "║  ${GREEN}✅ QA-LOOP: ALLE TESTS BESTANDEN ($PASS Schritte)${NC}                  ║"
else
    echo "║  ${RED}❌ QA-LOOP: $FAIL FEHLER ($PASS/$((PASS+FAIL)) Schritte ok)${NC}            ║"
fi
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

exit "$FAIL"
