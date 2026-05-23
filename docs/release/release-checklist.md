# Release Checklist — v0.1.0-local-alpha

## Pre-Release

- [x] Working tree: `qa/accessibility-tests` branch, commit `1cd7c9f`
- [x] `make quality` — 255 passed, 0 Errors
- [x] `make coverage` — 78.5% (≥78%)
- [x] `make ci-local` — All green (~45s)
- [x] `make runtime-smoke` — 4/4 services available
- [x] `make research-happy-path` — Report generated
- [x] `make research-evaluate` — Overall: 99/100
- [x] `make research-evaluate-regression` — PASS
- [x] Docs updated: CHANGELOG, Release Notes, Known Limitations, Checklist
- [x] README updated with current status

## Optional

- [x] `make ci-full` — All green (~5min)
- [ ] `multi-query live validation` — Run with local services
- [ ] `Playwright checks` — Visual regression + accessibility
- [ ] `upstream security PR review` — gpt_researcher fork

## Release Tag (manual only)

```bash
# Do NOT run automatically. Only when explicitly requested:
git tag -a v0.1.0-local-alpha -m "v0.1.0-local-alpha: Local Research Alpha"
git push origin v0.1.0-local-alpha
```

## GitHub Release (manual only)

```bash
gh release create v0.1.0-local-alpha \
  --title "v0.1.0-local-alpha — Local Research Alpha" \
  --notes-file docs/release/github-release-notes-v0.1.0-local-alpha.md
```

## Post-Release

- [ ] Tag `v0.1.0-local-alpha` exists on GitHub
- [ ] GitHub Release `v0.1.0-local-alpha` exists
- [ ] Release notes render correctly on GitHub
- [ ] README status matches release version
- [ ] Next milestone issues created (v0.2.0)
- [ ] Known limitations linked and up-to-date
- [ ] Issue #70 closed with completion comment
- [ ] Issue #69 closed with completion comment

## Re-Validation Guard (Orchestrator, 2026-05-20)

| Command | Result |
|---|---|
| `make quality` | ✅ 255 passed, 0 Errors |
| `make coverage` | ✅ 78.52% |
| `make test-e2e` | ✅ 9 passed |
| `make ci-local` | ✅ All green |
| `make runtime-smoke` | ✅ 4/4 services |
| `make research-happy-path` | ✅ Report generated |
| `make research-evaluate` | ✅ 99/100 |
| Tag `v0.1.0-local-alpha` | ✅ Does not exist (safe) |
| GitHub Release | ✅ Does not exist (safe) |
| Working tree clean? | ⚠️ ~119 uncommitted changes |
