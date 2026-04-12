# llm_wiki_prompt_packet Overview

## Plain-English Summary

This repo is a bootstrap and integration layer for the `llm-wiki-memory` system.

It is not mainly the search engine, not mainly the durable memory store, and not mainly the graph app. Its job is to install a coherent packet into a vault or workspace, wire the local machine to the expected tools, and give agents one predictable surface for search, memory, and reusable skills.

## What The Repo Actually Does

1. A hosted bootstrap wrapper downloads this repo and picks an install mode.
2. A Python installer copies prompts, docs, scripts, config, and starter directories into a target vault or repo workspace.
3. A setup helper resolves or installs `pk-qmd` and `brv`, patches MCP config in user homes, and optionally verifies or launches GitVizz.
4. A local skill MCP server persists skill-learning artifacts and exposes tools like `skill_lookup`, `skill_reflect`, `skill_validate`, and `skill_pipeline_run`.
5. Optional deploy surfaces package the same stack behind Docker, GCP, and a Cloudflare edge.

## Main System In One Sentence

This repo turns a plain Obsidian vault or repo workspace into an agent-ready memory/search workspace by installing files, wiring external tools, and standardizing the runtime contract.

## Core Product Areas

- Packet bootstrap:
  - `install.ps1`
  - `install.sh`
  - `installers/install_obsidian_agent_memory.py`
- Machine setup and health:
  - `support/scripts/setup_llm_wiki_memory.ps1`
  - `support/scripts/setup_llm_wiki_memory.sh`
  - `installers/assets/vault/scripts/check_llm_wiki_memory.ps1`
  - `installers/assets/vault/scripts/check_llm_wiki_memory.sh`
- Local skill-learning plane:
  - `support/scripts/llm_wiki_skill_mcp.py`
- Optional repo-local g-kade workspace bootstrap:
  - `installers/install_g_kade_workspace.py`
- Optional hosted and remote access surfaces:
  - `docker/`
  - `deploy/gcp/`
  - `deploy/cloudflare/`

## Short Boundary Model

- This repo:
  source templates, installers, setup helpers, plugin packaging, deploy glue
- Installed vault or workspace:
  `.llm-wiki/`, `wiki/`, `raw/`, `scripts/`, `.brv/`
- User home config:
  `~/.claude/settings.json`, `~/.codex/config.toml`, `~/.factory/mcp.json`
- External runtimes:
  `pk-qmd`, `brv`, GitVizz
- Optional remote edge:
  Docker container, GCP VM, Cloudflare Worker/Tunnel

## Fastest Mental Model

Think of the repo as a "packet plus glue" system:

- packet:
  prompts, docs, scripts, scaffold
- glue:
  setup helpers, MCP wiring, deploy wrappers
- runtime:
  external tools plus the installed vault state
