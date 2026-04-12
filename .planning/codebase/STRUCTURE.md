# Structure

## Top-Level Source Areas

- `prompts/`
  source prompt and workflow templates copied into target environments
- `installers/`
  Python installers plus health-check assets
- `support/`
  runtime docs and the shared helper scripts that do the heavy lifting
- `plugins/`
  packaged Codex plugin surface for `llm-wiki-organizer`
- `docker/`
  container runtime and MCP HTTP proxy
- `deploy/`
  remote deployment surfaces for GCP and Cloudflare edge
- `scripts/`
  source-side utility scripts, mainly release asset generation
- `tests/`
  installer and skill-pipeline tests

## Top-Level Runtime Or Local State Areas In This Checkout

- `.llm-wiki/`
  local packet state for this repo's own workspace bootstrap, not primary source
- `.brv/`
  local BRV workspace state
- `.agents/`
  local marketplace/bootstrap state for this repo's own environment

These hidden directories matter operationally, but they are not the main product source and should not be confused with `support/`, `installers/`, or `prompts/`.

## Primary Flow By Directory

### Standard vault install

- `install.ps1` or `install.sh`
- `installers/install_obsidian_agent_memory.py`
- `support/scripts/setup_llm_wiki_memory.ps1` or `.sh`
- installed target files under `.llm-wiki/`, `wiki/`, `raw/`, and `scripts/`

### g-kade workspace install

- `installers/install_g_kade_workspace.py`
- optional repo-local skill surfaces under `.agents/`, `.codex/`, `.claude/`
- `kade/AGENTS.md` and `kade/KADE.md`

### Skill-learning lifecycle

- `support/scripts/llm_wiki_skill_mcp.py`
- `.llm-wiki/skills-registry.json`
- `.llm-wiki/skill-pipeline/*`
- `wiki/skills/*`

## Source Of Truth Notes

- prompt content lives in `prompts/`
- helper implementation lives in `support/scripts/`
- installer behavior lives in `installers/`
- tests describe supported installer and skill-pipeline behavior
- deploy files are optional operational surfaces, not the core local bootstrap path
