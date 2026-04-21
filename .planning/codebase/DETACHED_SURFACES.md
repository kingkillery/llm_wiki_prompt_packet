# Detached Or Non-Primary Surfaces

## Meaning Of "Detached" In This Repo

Most tracked code in this repo is intentional, but not every tracked surface sits on the default local packet-install path.

This file separates:

- primary path:
  what runs for the normal local packet bootstrap
- optional path:
  tracked code that only runs in special modes
- local runtime state:
  folders present in this checkout that matter operationally but are not primary source

## Primary Path

- `install.ps1`
- `install.sh`
- `installers/install_obsidian_agent_memory.py`
- `support/scripts/setup_llm_wiki_memory.ps1`
- `support/scripts/setup_llm_wiki_memory.sh`
- `support/scripts/llm_wiki_skill_mcp.py`
- `installers/assets/vault/scripts/check_llm_wiki_memory.*`
- `prompts/`
- `support/`

## Connected But Optional

These are tracked and real, but they are not required for the default local vault bootstrap:

- `installers/install_g_kade_workspace.py`
  only used for repo-local `g-kade` workspace mode
- `installers/install_g_kade_workspace.ps1`
- `installers/install_g_kade_workspace.sh`
  companion wrappers for the same workspace mode
- `skills/home/*`
  packet-owned home-wrapper surfaces installed only when explicitly requested
- `plugins/llm-wiki-organizer/*`
  plugin packaging and distribution surface
- `docker/*` and `docker-compose*.yml`
  hosted/container runtime path
- `deploy/gcp/*`
  remote VM deployment path
- `deploy/cloudflare/*`
  remote public edge path
- `.github/workflows/release-installers.yml`
  release automation only
- `scripts/build_release_bootstraps.py`
  release asset generation only

## Runtime State In This Checkout, Not Core Source

- `.llm-wiki/`
  packet-local dependency manifest and local runtime state for this checkout
- `.brv/`
  local BRV workspace state
- `.agents/`
  local marketplace or plugin bootstrap state
- `.planning/`
  generated planning and codebase-map docs

These folders can matter for understanding the current checkout, but they are not the main source implementation the installers copy from.

## Current Worktree Notes

Current `git status --short` shows only:

- `m deps/pk-skills1`

That means the main first-party source tree is currently clean, and the only active worktree deviation is inside the richer runtime submodule checkout. Treat anything under `deps/pk-skills1/` as externalized runtime content rather than packet-owned source.

## Bottom Line

There is no large dead-code island in the tracked packet source.

The main source of confusion is structural, not unused code:

1. source templates and local runtime state both live under the same repo root
2. local bootstrap, plugin packaging, and hosted deployment are all shipped together
3. the richer `pk-skills1` runtime is referenced by contract but lives behind a submodule boundary
