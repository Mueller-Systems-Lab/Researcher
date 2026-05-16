# ============================================================================
# Makefile — Researcher Test-Suite
# ============================================================================
# Nutzung:
#   make test         # pytest
#   make coverage     # pytest --cov
#   make lint         # ruff check
#   make lint-types   # mypy
#   make security     # bandit
#   make all          # Alles auf einmal
#   make clean        # Cache und Build-Artifakte löschen
# ============================================================================

.PHONY: test coverage lint lint-types security playwright all clean help

help:
	@echo "Researcher — Test-Suite"
	@echo ""
	@echo "  make test         pytest (Unit + Integration)"
	@echo "  make coverage     pytest + Coverage-Report"
	@echo "  make lint         ruff check"
	@echo "  make lint-types   mypy type check"
	@echo "  make security     bandit security scan"
	@echo "  make playwright   Playwright-Visual-Tests"
	@echo "  make all          Alles auf einmal"
	@echo "  make clean        Cache löschen"
	@echo ""

test:
	python3 -m pytest tests/ -v

coverage:
	python3 -m pytest tests/ --cov --cov-report=term --cov-report=html --cov-report=xml
	@echo ""
	@echo "Coverage-Report: coverage_html/index.html"

lint:
	python3 -m ruff check . --line-length=88

lint-types:
	python3 -m mypy . --ignore-missing-imports

security:
	python3 -m bandit -r . --skip B101,B311,B404,B603

playwright:
	python3 -m pytest tests/playwright/ -v

all: test lint lint-types security
	@echo ""
	@echo "=== Alle Tests und Checks abgeschlossen ==="

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ */*/__pycache__
	rm -rf coverage_html coverage.xml
	rm -rf .mypy_cache .ruff_cache
	rm -rf tests/playwright/screenshots/diff
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
