---
title: Phase 8 Acceptance Report
phase: 8
issue: 143
status: draft
---

# Phase 8 Acceptance Report

## Goals and Deliverables

- [ ] Verify service auto-start for the full local stack
- [ ] Validate CI/CD acceptance gates for services, research flow, and report quality
- [ ] Confirm SearXNG source expansion and search stability
- [ ] Confirm dashboard screenshot fallback for SSE-free automation
- [ ] Document the local validation outcome for Phase 8

## Acceptance Criteria

- [ ] `start_all_services.sh` starts all 5 core services
- [ ] `researcher-ollama.service` is available for embeddings only
- [ ] `researcher-llama.service` serves Qwen3.5 on port 8082
- [ ] `researcher-searxng.service` serves SearXNG on port 8090
- [ ] `researcher-gptr.service` serves GPT Researcher on port 28202
- [ ] `researcher-dashboard.service` serves the dashboard on port 8888
- [ ] `make acceptance` exits with status 0
- [ ] `scripts/ci_acceptance.py` reports healthy services
- [ ] `scripts/ci_acceptance.py` reports a generated report
- [ ] `scripts/ci_acceptance.py` reports acceptable report size/source/claim metrics
- [ ] `dashboard/static/static-fallback.html` renders correctly for screenshots

## Test Results

| Check | Result | Notes |
|---|---|---|
| `make acceptance` | TBD |  |
| `python3 scripts/ci_acceptance.py --skip-research` | TBD |  |
| `python3 scripts/ci_acceptance.py --json-output` | TBD |  |
| Dashboard static fallback | TBD |  |
| Service auto-start | TBD |  |

## Known Issues

- SSE-based dashboard views can still block Playwright `networkidle`; use the static fallback for screenshots.
- Qwen3.5 on Pascal GPUs may require the documented precision settings to avoid garbled output.
- SearXNG engine availability can vary by upstream CAPTCHA/rate-limit behavior.
