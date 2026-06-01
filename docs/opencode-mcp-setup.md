# OpenCode MCP Setup

## 1. Project Analysis

Researcher is a local-first research system built around a Python 3.11 codebase with a nested GPT Researcher submodule, a Next.js frontend, Docker-based local services, and pytest/Playwright coverage. The repo also contains a project-local MCP tool server in `mcp_tools/` that exposes five gated tools over HTTP.

Detected stack and workflow signals:

- Python 3.11+ with `pytest`, `ruff`, `mypy`, and `bandit`
- GPT Researcher submodule under `gpt_researcher/`
- Next.js frontend under `gpt_researcher/frontend/nextjs`
- Docker Compose for local runtime services
- Playwright-based browser test coverage under `tests/playwright/`
- Local research runtime services: Ollama, SearXNG, Tor, ChromaDB, Whoosh
- Project-local MCP server on `127.0.0.1:8766`

## 2. Existing OpenCode/MCP Configuration

| Source | Found | Result |
|---|---:|---|
| `opencode.json` in repo root | no | No project-local JSON config before this setup |
| `opencode.jsonc` in repo root | no | No project-local JSONC config before this setup |
| `config/playwright-mcp.local.json` | yes | New Playwright MCP config added for project scope |
| `~/.config/opencode/opencode.json` | yes | Global OpenCode config exists and already enables several MCPs |
| `opencode mcp list` | attempted | Failed once with `PRAGMA wal_checkpoint(PASSIVE)` and then stalled on a clean-data retry |
| `opencode auth list` | yes | Provider credentials are present in user state |

Observed global MCPs in user config:

- `github`
- `playwright`
- `docker`
- `sqlite`
- `brave-search`
- `context7`
- `gptr-mcp`

Notes:

- The global config contains a hardcoded GitHub token value. I did not copy or modify that secret.
- Because `opencode mcp list` failed in the user-level OpenCode state, I relied on direct config inspection and a manual smoke test of the repo-local MCP server.

## 3. Recommended MCPs

| MCP | Benefit | Risk | Decision | Reason |
|---|---|---|---|---|
| `researcher-mcp` | High | Medium | Install / keep enabled | Directly relevant to this repo; exposes the project's evidence, claim-validation, web-fetch, audit, and human-review tools |
| `playwright` | Medium | Medium | Install / keep enabled | Scoped through a project-local Playwright config file, headless, isolated, and restricted to local app origins |
| `docker` | Medium | Medium | Do not add at project scope | Relevant for runtime debugging, but it is already available globally and is broader than needed for the project-local setup |
| `github` | Medium | Medium | Do not add at project scope | Helpful for PR/issue workflows, but it requires token-based access and is not needed for the local MCP setup itself |
| `sqlite` | Low | Medium | Do not add | No immediate repo need for arbitrary DB access from OpenCode |
| `brave-search` | Low | Medium | Do not add | The project is intentionally local-first and already uses SearXNG/Ollama rather than cloud search |
| `context7` | Low | Low | Do not add | Local docs and pinned manifests already cover the main framework usage without extra external traffic |
| `gptr-mcp` | Medium | Medium | Do not add | Separate research service, but not required for the repo-local MCP setup |

## 4. Active MCPs

| MCP | Test | Result |
|---|---|---|
| `researcher-mcp` | HTTP health check and tools list | PASS |
| `playwright` | Config file enforces headless Chromium, isolated profile, and local-only origins | CONFIGURED |

## 5. Final Configuration

Current project-level OpenCode configuration:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    // Repo-local MCP server exposing the security-gated tools in mcp_tools/.
    "researcher-mcp": {
      "type": "remote",
      "url": "http://127.0.0.1:8766/mcp",
      "enabled": true
    },
    // Project-scoped Playwright override: headless and restricted to local app origins.
    "playwright": {
      "type": "local",
      "command": [
        "npx",
        "-y",
        "@playwright/mcp@latest",
        "--config",
        "{env:WORKSPACE_ROOT}config/playwright-mcp.local.json"
      ],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

How to start the project-local MCP server:

```bash
python3 -m mcp_tools.server
```

The helper script exists too, but it is not executable in the current repo state, so invoke it with `bash` if you prefer that wrapper:

```bash
bash scripts/start-mcp.sh --check
```

## 6. Required Secrets

None for the project-level MCP config added here.

Known secret-related note:

- The existing global OpenCode config in `~/.config/opencode/opencode.json` contains a GitHub token value. That is outside this repo's config and should be moved to a secure env/secret mechanism if the global MCP remains in use.

## 7. Test Commands

```bash
opencode --version
opencode auth list
opencode mcp list
python3 -m mcp_tools.server
curl -fsS http://127.0.0.1:8766/
curl -fsS http://127.0.0.1:8766/health
opencode mcp debug researcher-mcp
bash -lc 'opencode mcp list'
bash scripts/start-mcp.sh --check
npx -y @playwright/mcp@latest --help
node -e "JSON.parse(require('fs').readFileSync('config/playwright-mcp.local.json', 'utf8')); console.log('ok')"
```

## 8. Testergebnisse

```text
opencode --version: PASS (1.15.0)
opencode auth list: PASS
opencode mcp list: PARTIAL/FAIL (local OpenCode state reported PRAGMA wal_checkpoint(PASSIVE); clean-data retry stalled after printing the header)
python3 -m mcp_tools.server: PASS (server announced http://127.0.0.1:8766/mcp and 5 tools)
curl /: PASS
curl /health: PASS
opencode mcp debug researcher-mcp: PASS (HTTP 200, no auth required)
bash -lc 'opencode mcp list': PASS (researcher-mcp connected)
bash scripts/start-mcp.sh --check: PASS
npx @playwright/mcp --help: PASS (official CLI exposes `--config`, `--browser`, `--allowed-origins`, and related browser controls)
config/playwright-mcp.local.json: PASS (valid JSON)
```

## 9. Security Decisions

- Added only the repo-local MCP server needed by this project.
- Added a project-scoped Playwright override plus a dedicated Playwright config file so browser automation is limited to the local app surfaces.
- Kept the project config remote and loopback-only at `127.0.0.1`.
- Did not add broad browser, GitHub, cloud search, or cloud docs MCPs to the project config.
- Did not write any secrets into the repository config.
- Left the existing user-level OpenCode config untouched, even though it contains broader tooling and a plaintext GitHub token.

## 10. Maintenance

- Restart OpenCode after changing `opencode.jsonc`.
- Keep the `researcher-mcp` server started before expecting OpenCode to discover tools.
- Keep the `playwright` MCP config file headless, isolated, and origin-restricted unless you explicitly need broader browser access.
- If the MCP tool surface changes, update `opencode.jsonc` and this document together.
- If you later need browser automation, add a scoped Playwright MCP entry with a local target app boundary instead of reusing the broad global one.

## 11. Troubleshooting

- If `opencode mcp list` keeps failing with `PRAGMA wal_checkpoint(PASSIVE)`, the issue is in the user-level OpenCode state, not this repo-local config.
- If `python3 -m mcp_tools.server` fails, verify the project dependencies are installed in the active Python environment.
- If `opencode mcp auth researcher-mcp` returns `WWW-Authenticate: Bearer` or `Missing or invalid authentication`, the URL is pointing at the wrong process. `researcher-mcp` is not OAuth-enabled; stop the conflicting service or start the MCP server on the configured `MCP_PORT`.
- If port `8766` is already in use, change `MCP_PORT` before starting the server.
- If `scripts/start-mcp.sh` is called directly and fails with permission denied, invoke it as `bash scripts/start-mcp.sh ...` or fix the executable bit.
