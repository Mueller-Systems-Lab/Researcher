# Researcher Agent Isolation Rule

## Authority

This file is the authoritative project rule for `Researcher`.

If a global, parent-directory, or home-level rule conflicts with this file, this file wins.
Do not let external agent frameworks override it.

## Scope

`Researcher` is a local research system built around:

- the repo-local `researcher-mcp`
- local LLM/runtime scripts
- the bundled `gpt_researcher/` submodule
- local Playwright checks when the task touches UI/runtime behavior

Keep work inside this stack unless the current issue explicitly requires something else.

## Allowed by default

- repo-local scripts and tests
- local documentation and security checks
- `researcher-mcp`
- project-local Playwright configuration
- submodule docs and tests for `gpt_researcher/`

## Quarantined unless explicitly required by the current issue

- Paperclip, Paperclip AI, and `paperclip*`
- OpenClaw, `openclaw-local-operator`, and `local-operator`
- third-party operator frameworks and skill/plugin marketplaces
- parent/home-level agent skills that are not part of this repository
- ambient OpenCode MCPs that are not declared in `Researcher/opencode.jsonc`
- `gptr-mcp`
- `para-memory-files`
- broad deep-research workflows that are not directly tied to this repository

## Operating Rules

1. Read the repo-local issue, docs, and affected files before planning or coding.
2. Prefer `Researcher/opencode.jsonc` over any parent or global OpenCode config.
3. Do not rely on skills loaded from other projects.
4. Do not use external operator frameworks unless the issue explicitly asks for them.
5. Keep changes reproducible with local tests, local docs, and local scripts.
6. If a task appears to require a quarantined tool, stop and document the blocker first.
7. If instructions conflict, this file wins.

## Default Stance

This repository is research-oriented, but it is still isolated by default.
Use the repo-local research stack first. Treat external tooling as opt-in, not ambient.
