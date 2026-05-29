# Release Checklist — v0.2.2

## Pre-Release

- [x] Working tree: `main` branch, commit `bd1fe61`
- [x] `make quality` — **780 passed**, 24 skipped, 2 xfailed
- [x] `make security-project` — **0 Medium/High Findings** (6 Low dokumentiert)
- [x] `make lint` — **0 Errors**
- [x] CHANGELOG.md aktualisiert
- [x] Release Notes aktualisiert (`docs/release/v0.2.2.md`)
- [x] Known Limitations aktualisiert (v0.2.2)
- [x] pyproject.toml: 0.2.1 → 0.2.2
- [x] Checklist aktualisiert
- [x] Alle 8 Post-Release-Commits enthalten (#122–#125, #130–#131, SSRF, research-serve.sh)

## Bekannte Pre-Existing Failures (nicht blockierend)

- 9 Benchmark-Tests: `gpt_researcher.adapters.*` nicht pip-installiert
- 2 E2E Pipeline-Tests: gleiche Ursache + Retriever-Leerlauf

## Optional

- [ ] `make runtime-smoke` — Requires local services
- [ ] `make research-happy-path` — Requires local services
- [ ] `make research-evaluate` — Overall score check
- [ ] `Playwright checks` — Visual regression + accessibility
- [ ] `upstream security PR review` — gpt_researcher fork

## Release Tag

```bash
git tag -a v0.2.2 -m "v0.2.2: DB-Safety, Review-Findings, Concurrency-Hardening"
git push origin v0.2.2
```

## GitHub Release

```bash
gh release create v0.2.2 \
  --title "v0.2.2 — DB-Safety, Review-Findings, Concurrency-Hardening" \
  --notes-file docs/release/v0.2.2.md
```

## Post-Release

- [ ] Tag `v0.2.2` exists on GitHub
- [ ] GitHub Release `v0.2.2` exists
- [ ] Release notes render correctly on GitHub
- [ ] README status matches release version
- [ ] Known limitations linked and up-to-date
- [ ] Next milestone issues created (v0.3.0)
- [ ] Issues #122–#125, #130–#131 alle closed

## Final Validation (2026-05-29)

| Command | Result |
|---|---|
| `make quality` | ✅ 780 passed, 24 skipped, 2 xfailed |
| `make security-project` | ✅ 0 Medium/High Findings |
| `make lint` | ✅ 0 Errors |
| Tag `v0.2.2` | ⏳ Wird erstellt |
| GitHub Release | ⏳ Wird erstellt |
| Working tree clean? | ⏳ Nach Commit |
