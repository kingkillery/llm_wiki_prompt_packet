# Detached Or Non-Primary Surfaces

## Meaning Of "Detached" In This Repo

Most of the code here is intentional, but not all of it sits on the default local bootstrap path.

This file separates:

- primary path:
  what runs for a normal local packet install
- optional path:
  connected code that only runs in special modes
- current worktree-only path:
  files present in this checkout that are not part of the clean tracked baseline

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

These are real parts of the system, but not used by a normal local vault bootstrap:

- `installers/install_g_kade_workspace.py`
  only used for `g-kade` workspace mode
- `skills/home/*`
  only used when home skill install is explicitly enabled
- `plugins/llm-wiki-organizer/*`
  packaging surface, not required for install/setup
- `docker/*` and `docker-compose*.yml`
  hosted/container path
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
  installed dependency and runtime state
- `.brv/`
  local BRV workspace state
- `.agents/`
  local plugin marketplace state

These folders can be important for understanding how the repo behaves locally, but they are not the main source implementation.

## Current Worktree Notes

In this checkout, some extension surfaces are present but are not part of a clean tracked baseline according to `git status`:

- `deploy/cloudflare/`
- `installers/install_g_kade_workspace.ps1`
- `installers/install_g_kade_workspace.sh`
- `skills/`

That matters because tracked Python code already references `skills/home/*`, so the current branch mixes stable source and local extension work in a way that can confuse a first read.

## Bottom Line

There is no obvious large dead-code island inside the core bootstrap path.

The main confusion comes from three things:

1. source code and runtime state are mixed in the repo root
2. local bootstrap, plugin packaging, and hosted deployment live in the same repo
3. some optional extension surfaces are currently worktree-only in this checkout
