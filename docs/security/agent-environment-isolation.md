# Agent Environment Isolation

This repository has a project-local isolation layer to keep ambient workspace rules from leaking into Researcher sessions.

## Authoritative files

- [`AGENTS.md`](../../AGENTS.md)
- [`opencode.jsonc`](../../opencode.jsonc)
- [`docs/security/security-gate-policy.md`](security-gate-policy.md)
- [`docs/development/local-runbook.md`](../development/local-runbook.md)

## What is allowed by default

- the local `researcher-mcp`
- local scripts and tests
- project-local Playwright checks
- the bundled `gpt_researcher/` submodule

## What is quarantined by default

- Paperclip / Paperclip AI skill trees
- OpenClaw / local-operator toolchains
- parent or home-level agent skills that are not part of this repository
- ambient `gptr-mcp` from the workspace root
- unrelated deep-research workflows

## Config intent

`Researcher/opencode.jsonc` keeps the repo-local research tools enabled and explicitly disables the ambient workspace `gptr-mcp`.

That keeps the project on its own research path instead of inheriting other workspace agent stacks.
