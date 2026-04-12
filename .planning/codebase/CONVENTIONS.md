# Conventions

## Design Conventions

- Python installers own file-copy and scaffold logic.
- PowerShell and shell helpers mirror the same setup responsibilities for Windows and Unix environments.
- The repo is local-first:
  packet-local installs are preferred before global installs.
- Config is centralized through `.llm-wiki/config.json`.
- Runtime artifacts are persisted under `.llm-wiki/skill-pipeline/`.
- The skill system is markdown-first and registry-backed.

## Naming Conventions

- `install_*`:
  installer entrypoints
- `setup_*`:
  machine or workspace bootstrap helpers
- `check_*`:
  health verification
- `brv_*`, `gitvizz_*`:
  tool-specific helpers
- `llm_wiki_skill_mcp.py`:
  local skill MCP server and CLI

## Product Conventions

- Prompt assets are treated as first-class product content.
- Repo-local and user-home skill surfaces are intentionally separated.
- Long tasks in the skill pipeline must emit reducer packets rather than vague summaries.
- GitVizz is treated as optional unless explicitly configured as managed for the workspace.

## Operational Conventions

- Setup helpers patch user config rather than asking users to wire MCP by hand.
- Health checks validate both external tools and local scaffold shape.
- Hosted deployment is layered:
  local packet first, then Docker, then GCP, then optional Cloudflare edge.
