# Release Checklist — v0.1.0-local-alpha

## Pre-Release

- [x] Working tree: `main` branch, commit `787f391`
- [x] `make coverage-fast` — **716 passed**, 0 failed
- [x] `make security-project` — **0 Medium/High Findings**
- [x] `make lint` — **0 Errors**
- [x] `make typecheck` — **0 Errors** (91 source files)
- [x] `make coverage` — **85.06%** (≥81%)
- [x] ChromaDB count=-1 Fix ✅
- [x] Security B310/B314 behoben ✅
- [x] Integrationstests (#108), Mock-Audit (#107), Evidence Store ✅
- [x] CHANGELOG.md aktualisiert
- [x] Release Notes aktualisiert
- [x] Known Limitations aktualisiert
- [x] Checklist aktualisiert
- [x] `requirements.txt`: defusedxml ergänzt
- [x] `.gitignore`: coverage_html/ ergänzt

## Optional

- [ ] `make ci-local` — All green (~45s)
- [ ] `make runtime-smoke` — 4/4 services available (requires local services)
- [ ] `make research-happy-path` — Report generated (requires local services)
- [ ] `make research-evaluate` — Overall score check
- [ ] `multi-query live validation` — Run with local services
- [ ] `Playwright checks` — Visual regression + accessibility
- [ ] `upstream security PR review` — gpt_researcher fork

## Release Tag

```bash
# Execute after final quality gate verification:
git tag -a v0.1.0-local-alpha -m "v0.1.0-local-alpha: Erste lokale Research-Release"
git push origin v0.1.0-local-alpha
```

## GitHub Release

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
- [ ] Issue #69 closed with completion comment
- [ ] Issue #71 closed with completion comment
- [ ] Issue #72 closed with completion comment
- [ ] Issue #73 closed with completion comment
- [ ] Issue #108 closed with completion comment

## Final Validation (2026-05-27)

| Command | Result |
|---|---|
| `make coverage-fast` | ✅ 716 passed, 0 failed |
| `make security-project` | ✅ 0 Medium/High Findings |
| `make lint` | ✅ 0 Errors |
| `make typecheck` | ✅ 0 Errors |
| Tag `v0.1.0-local-alpha` | ⏳ Wird erstellt |
| GitHub Release | ⏳ Wird erstellt |
| Working tree clean? | ⏳ Nach Commit |
