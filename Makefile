# ============================================================================
# Makefile — Researcher Test-Suite mit getrennten Profilen
# ============================================================================
# Quick Loop (lokal):
#   make quality          # lint + typecheck + security + fast-tests
#   make coverage         # Coverage-Gate (>=78%)
#
# Full Gate (CI):
#   make ci-local         # quality + coverage + e2e
#   make ci-full          # alles inkl. benchmarks + reports
#
# Einzelne Profile:
#   make test-fast        # Unit/Integration (schnell, ohne schwere Tests)
#   make test-e2e         # E2E-Pipeline-Tests
#   make test-benchmarks  # Performance-Benchmarks
#   make lint             # ruff check (blocking)
#   make typecheck        # mypy project code (blocking)
#   make security-project # bandit project code (blocking)
#
# Legacy (rückwärtskompatibel):
#   make test             # Full test suite (historisch)
#   make all              # → ci-local
# ============================================================================

.PHONY: test test-fast test-e2e test-benchmarks coverage lint lint-types typecheck typecheck-vendor security security-project security-vendor security-report playwright quality ci-local ci-full all clean help

# Gemeinsame Ignore-Pfade für schnelle Tests
FAST_IGNORE := --ignore=tests/benchmarks --ignore=tests/e2e --ignore=tests/playwright/test_dashboard_accessibility.py --ignore=tests/playwright/test_dashboard_visual_regression.py

help:
	@echo "Researcher — Test-Suite"
	@echo ""
	@echo "  Schnelle Profile (lokal):"
	@echo "    make quality          lint + typecheck + security + fast-tests"
	@echo "    make coverage         Coverage-Gate (>=78%)"
	@echo "    make test-fast        Unit/Integration (schnell)"
	@echo ""
	@echo "  CI-Profile:"
	@echo "    make ci-local         quality + coverage + e2e"
	@echo "    make ci-full          alles inkl. benchmarks + reports"
	@echo ""
	@echo "  Einzelne Gates:"
	@echo "    make lint             ruff check (blocking)"
	@echo "    make typecheck        mypy project code (blocking)"
	@echo "    make typecheck-vendor mypy vendor/submodule (report)"
	@echo "    make security         bandit full scan"
	@echo "    make security-project bandit project code (blocking)"
	@echo "    make security-vendor  bandit vendor/submodule (report)"
	@echo "    make security-report  bandit JSON/TXT reports"
	@echo ""
	@echo "  Spezielle Profile:"
	@echo "    make test-e2e         E2E-Pipeline-Tests"
	@echo "    make test-benchmarks  Performance-Benchmarks"
	@echo "    make playwright       Playwright-Visual-Tests"
	@echo ""
	@echo "  Utility:"
	@echo "    make clean            Cache löschen"
	@echo ""

# ── Schnelle Testprofile ─────────────────────────────────────────────────────

test-fast:
	python3 -m pytest tests/ $(FAST_IGNORE) -q

test-e2e:
	python3 -m pytest tests/e2e/ -v --timeout=30 --count=3 -q

test-benchmarks:
	python3 -m pytest tests/benchmarks/ -v --timeout=300

# ── Lint & Typecheck ──────────────────────────────────────────────────────────

lint:
	python3 -m ruff check . --line-length=88

lint-types:
	python3 -m mypy . --ignore-missing-imports || true

TYPECHECK_PROJECT_PATHS := config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery research_orchestrator research_planner research_workers scripts
typecheck:
	python3 -m mypy $(TYPECHECK_PROJECT_PATHS) --ignore-missing-imports

typecheck-vendor:
	python3 -m mypy gpt_researcher --ignore-missing-imports || true

# ── Security ──────────────────────────────────────────────────────────────────

security:
	python3 -m bandit -r . --skip B101,B311,B404,B603

security-project:
	python3 -m bandit -r config crawlers darknet_search search dashboard vectordb mcp_tools onion_discovery scripts --skip B101,B311,B404,B603 --severity-level medium

security-vendor:
	python3 -m bandit -r gpt_researcher --skip B101,B311,B404,B603 || true

security-report:
	mkdir -p reports
	python3 -m bandit -r . --skip B101,B311,B404,B603 -f json -o reports/bandit-full.json || true
	python3 -m bandit -r . --skip B101,B311,B404,B603 -f txt -o reports/bandit-full.txt || true
	@echo "Reports: reports/bandit-full.json, reports/bandit-full.txt"

# ── Security Regression Tests ─────────────────────────────────────────────────

security-regression:
	python3 -m pytest tests/security/ -q

# ── Aggregierte Profile ──────────────────────────────────────────────────────

quality:
	python3 -m ruff check . --line-length=88
	$(MAKE) typecheck
	$(MAKE) security-project
	$(MAKE) security-regression
	$(MAKE) test-fast

ci-local:
	$(MAKE) quality
	$(MAKE) coverage-fast
	$(MAKE) test-e2e

ci-full:
	$(MAKE) ci-local
	$(MAKE) security-vendor
	$(MAKE) security-report
	$(MAKE) test-benchmarks

# ── Runtime Smoke Test ────────────────────────────────────────────────────────

runtime-smoke:
	python3 scripts/runtime_smoke.py

runtime-smoke-strict:
	REQUIRE_OLLAMA=true REQUIRE_SEARXNG=true REQUIRE_TOR=true python3 scripts/runtime_smoke.py

# ── SearXNG Docker Management ─────────────────────────────────────────────────

searxng-up:
	docker compose -f searxng/docker-compose.yml up -d

searxng-down:
	docker compose -f searxng/docker-compose.yml down

searxng-logs:
	docker compose -f searxng/docker-compose.yml logs --tail=100

searxng-smoke:
	python3 scripts/runtime_smoke.py --only searxng

# ── Research Happy Path ───────────────────────────────────────────────────────

research-happy-path:
	SEARXNG_TIMEOUT_SECONDS=30 python3 scripts/research_happy_path.py

research-happy-path-strict:
	SEARXNG_TIMEOUT_SECONDS=30 python3 scripts/research_happy_path.py --strict

research-happy-path-clean:
	rm -rf reports/research/

# ── Report Evaluation ─────────────────────────────────────────────────────────

research-evaluate:
	python3 scripts/evaluate_research_report.py --latest

research-evaluate-strict:
	python3 scripts/evaluate_research_report.py --latest --min-score 70

research-happy-path-eval:
	$(MAKE) research-happy-path
	$(MAKE) research-evaluate

# ── Multi-Query Evaluation ────────────────────────────────────────────────────

research-evaluate-multi:
	ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py --limit 3

research-evaluate-multi-strict:
	ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py --limit 3 --min-overall 80 --min-query-overall 70

# ── Deutsche Query-Fixture Evaluation (optional, nicht in make quality) ────────

research-evaluate-german:
	ALLOW_OLLAMA_MODEL_FALLBACK=true python3 scripts/research_multi_query_eval.py \
		--queries-file tests/fixtures/german_queries.json --limit 3

# ── Coverage (mit Schwelle >=78%) ─────────────────────────────────────────────

coverage: coverage-fast

coverage-fast:
	python3 -m pytest tests/ $(FAST_IGNORE) --cov --cov-report=term -q

coverage-full:
	python3 -m pytest tests/ $(FAST_IGNORE) --cov --cov-report=term --cov-report=html --cov-report=xml
	@echo ""
	@echo "Coverage-Report: coverage_html/index.html"

# ── Legacy / Backward Compatible ──────────────────────────────────────────────

test:
	python3 -m pytest tests/ -v

playwright:
	python3 -m pytest tests/playwright/ -v

all: ci-local
	@echo ""
	@echo "=== Quality Gate abgeschlossen ==="

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ */*/__pycache__
	rm -rf coverage_html coverage.xml
	rm -rf .mypy_cache .ruff_cache
	rm -rf tests/playwright/screenshots/diff
	rm -rf reports/bandit-*.json reports/bandit-*.txt
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
