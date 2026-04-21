# Coding Conventions

**Analysis Date:** 2026-04-12

## Naming Patterns

**Files:**

- `snake_case.py` for Python modules and tests, for example `install_obsidian_agent_memory.py` and `test_llm_wiki_skill_mcp.py`
- `snake_case.sh` and `snake_case.ps1` for bootstrap helpers, for example `setup_llm_wiki_memory.sh` and `install_g_kade_workspace.ps1`
- Lowercase compound `.mjs` files for Node helpers, for example `mcp_http_proxy.mjs`

**Functions:**

- Python uses `snake_case` helper functions with a single `main()` entrypoint pattern in `installers/*.py` and `support/scripts/llm_wiki_skill_mcp.py`
- PowerShell uses `Verb-Noun` helpers such as `Resolve-ScriptWorkspaceRoot`, `Get-LocalQmdCommandPath`, and `Initialize-BrvWorkspace`
- JavaScript helpers use `camelCase` such as `proxyRequest`, `handleMemoryStatus`, and `buildUpstreamUrl`

**Variables:**

- Module constants use `UPPER_SNAKE_CASE` in Python and JavaScript, for example `PACKET_ROOT`, `ROOT_FILES`, and `JSON_HEADERS`
- Environment variables are consistently exposed as `LLM_WIKI_*`, `BYTEROVER_API_KEY`, `GH_TOKEN`, and `GITHUB_TOKEN`
- Local variables are descriptive and usually lowercase or camelCase depending on language

**Types:**

- Python relies on type annotations rather than custom class hierarchies in `installers/*.py` and `support/scripts/llm_wiki_skill_mcp.py`
- No TypeScript or typed JS layer is tracked in this repo

## Code Style

**Formatting:**

- No dedicated formatter configs are tracked; style is maintained by convention rather than lint tooling
- Python uses 4-space indentation, no semicolons, and mostly double-quoted strings
- JavaScript uses semicolons and small helper functions in `docker/mcp_http_proxy.mjs` and `deploy/cloudflare/mcp-edge-worker.js`
- PowerShell uses explicit `param(...)` blocks, 4-space indentation, and verbose helper names

**Linting:**

- Not detected. There is no tracked `ruff`, `black`, `flake8`, `eslint`, or `prettier` config in the repo root
- Consistency is enforced primarily through tests and review rather than an automated formatter

## Import Organization

**Order:**

1. Standard library or built-in modules first, for example `argparse`, `json`, `Path`, `node:http`
2. Compatibility or utility imports next, for example `importlib.util`, `unittest.mock`, `node:child_process`
3. Repo-local constants and orchestration code below the imports

**Grouping:**

- Python files usually separate stdlib imports from local constants with a blank line
- JavaScript files group built-ins at the top and keep helper functions below the import block

**Path Aliases:**

- None detected; all imports and path joins are relative or filesystem-based

## Error Handling

**Patterns:**

- Python exits early with `SystemExit` or explicit exceptions when validation fails in `installers/install_obsidian_agent_memory.py` and `installers/install_g_kade_workspace.py`
- Bash uses `set -euo pipefail` to treat most failures as fatal in `install.sh`, `docker/entrypoint.sh`, and `support/scripts/setup_llm_wiki_memory.sh`
- PowerShell sets `$ErrorActionPreference = "Stop"` and surfaces failures with `Write-Error`
- Node gateway code returns structured JSON errors rather than throwing raw stack traces to HTTP clients in `docker/mcp_http_proxy.mjs`

**Error Types:**

- Installer validation failures are usually argument or filesystem contract errors
- Runtime helper failures are treated as environment/bootstrap failures and reported in summary output
- HTTP-facing errors are returned as `401`, `404`, `500`, `502`, or `503` with JSON bodies

## Logging

**Framework:**

- Plain CLI output (`print`, `Write-Output`, shell `echo`) for installer and setup flows
- `console.error` for gateway-side operational errors in `docker/mcp_http_proxy.mjs`

**Patterns:**

- Setup helpers accumulate summary lines and print them at the end
- Error cases usually include the actionable command or path that failed
- There is no structured logger dependency in the tracked source

## Comments

**When to Comment:**

- Module docstrings are used for the most user-facing Python entrypoints such as `install_obsidian_agent_memory.py` and `build_release_bootstraps.py`
- Inline comments are sparse and generally reserved for clarifying cross-platform or proxy behavior
- Most code prefers descriptive helper names over explanatory comments

**JSDoc/TSDoc:**

- Not used in tracked JavaScript

**TODO Comments:**

- Not detected in tracked non-vendored source. A `git grep` for `TODO|FIXME|HACK|XXX` returned no hits outside vendored content

## Function Design

**Size:**

- Installers favor many small helper functions followed by one orchestration `main()`
- The main exception is the large orchestration logic in `support/scripts/setup_llm_wiki_memory.sh`, `support/scripts/setup_llm_wiki_memory.ps1`, and `support/scripts/llm_wiki_skill_mcp.py`

**Parameters:**

- Python and PowerShell favor explicit named parameters over positional-only helpers
- Shell helpers depend heavily on environment variables plus long flags such as `--skip-gitvizz` and `--allow-global-tool-install`

**Return Values:**

- Python helpers commonly return structured dicts or lists of action lines
- Shell and PowerShell helpers return via exit code plus summary/error output

## Module Design

**Exports:**

- Python modules use the standard `if __name__ == "__main__":` executable pattern
- JavaScript gateway and Cloudflare files export one default server/worker surface

**Barrel Files:**

- Not used. Modules are imported directly by path or executed as scripts

---

_Convention analysis: 2026-04-12_
_Update when scripting style or bootstrap patterns change_
