# Testing

## Current Test Coverage

- `tests/test_install_obsidian_agent_memory.py`
  installer safety, home-skill behavior, ownership checks, safe target roots
- `tests/test_install_g_kade_workspace.py`
  workspace root detection, richer upstream detection, repo-local scaffold behavior
- `tests/test_llm_wiki_skill_mcp.py`
  skill pipeline behavior, reducer packet persistence, validation rules, duplicate merge flow, PII blocking

## What Is Well Covered

- Python installer behavior
- g-kade workspace scaffolding behavior
- local skill MCP reducer/router behavior

## What Is Less Covered

- root hosted wrappers:
  `install.ps1`, `install.sh`
- PowerShell and shell setup helpers end to end
- Docker runtime behavior
- GCP deploy flow
- Cloudflare edge flow
- plugin packaging behavior

## Practical Read

The test suite protects the core source-side Python logic better than the outer operational wrappers. If something breaks in the system, the highest-risk areas are usually:

- shell and PowerShell parity
- user-home MCP patching
- hosted deploy glue
- optional surfaces that are not exercised by unit tests
