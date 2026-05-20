# v0.1.0-local-alpha — Local Research Alpha

First validated local research pipeline release.

## Highlights

- ✅ **Local Research Happy-Path**: Query → SearXNG → Ollama → Report
- ✅ **6-in-1 Quality Gate** (`make quality`): lint, typecheck, security, tests, coverage — all blocking
- ✅ **Runtime Smoke Checks**: Ollama, SearXNG, Tor, Cloud-Blocker
- ✅ **Report Quality Evaluation**: 4 scores (Source, Traceability, Hallucination, Local-First)
- ✅ **Multi-Query Regression Guard**: baseline thresholds
- ✅ **Security Regression Tests**: 14 tests (timeouts, cloud-blocker, hashing, SQL, SSL)
- ✅ **Fresh Clone Onboarding**: clone → venv → green gates in <5 minutes
- ✅ **Zero Cloud Dependencies**: no OpenAI, Tavily, Anthropic, or other cloud providers

## Verification

```bash
make quality
SEARXNG_TIMEOUT_SECONDS=30 make runtime-smoke
ALLOW_OLLAMA_MODEL_FALLBACK=true make research-happy-path
make research-evaluate
```

Expected: All green. Report: Overall 99/100.

## Quality Metrics

- **Test Suite**: 255 tests, 78.5% coverage
- **Lint**: 0 ruff errors
- **Type Check**: 0 mypy errors (project code)
- **Security**: 0 Medium/High Bandit findings (project code)

## Known Limitations

- Alpha release — no production research validation
- SearXNG requires local Docker
- Ollama models must be locally available
- Report evaluation is heuristic, not truth verification

See `docs/release/known-limitations.md` for full details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
