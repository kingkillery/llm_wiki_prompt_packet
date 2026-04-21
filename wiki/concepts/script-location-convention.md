# Script Location Convention

## Two locations, two purposes

| Path | Role | When to use |
|---|---|---|
| `support/scripts/` | Source tree | Code review, debugging, test authoring, submodule work |
| `scripts/` | Installer-deployed vault surface | Normal vault operations, health checks, MCP server launch |

The installer copies scripts from `support/scripts/` into `scripts/` inside each activated target vault. The source and deployed copies should stay in sync but are physically separate.

## Agent routing rule

- References in `AGENTS.md`, `CLAUDE.md`, and `.llm-wiki/config.json` always point to `scripts/` (deployed surface).
- KADE.md handoff logs that mention `support/scripts/` are describing the source location of a change.
- When a script behaves unexpectedly in a deployed vault, check whether `support/scripts/` and the deployed `scripts/` copy are in sync.

## Key scripts

| Script | Source | Purpose |
|---|---|---|
| `llm_wiki_skill_mcp.py` | `support/scripts/` | Skill lifecycle MCP server and CLI |
| `llm_wiki_memory_runtime.py` | `support/scripts/` | Shared setup/check logic |
| `llm_wiki_failure_collector.py` | `support/scripts/` | Failure event ingestion and cluster promotion |
| `setup_llm_wiki_memory.ps1/.sh` | `scripts/` (source: `support/scripts/`) | Full stack bootstrap |
| `check_llm_wiki_memory.ps1/.sh` | `scripts/` (source: `support/scripts/`) | Health verification |
| `brv_query.ps1/.sh` | `scripts/` | BRV query wrapper |
| `brv_curate.ps1/.sh` | `scripts/` | BRV curate wrapper |
