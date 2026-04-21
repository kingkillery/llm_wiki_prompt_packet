# System Contract

This repo packages the combined `Kade-HQ` + `G-Stack` + `pk-qmd` + `Byterover` + `GitVizz` system.

## Canonical Layers

- Harness layer: `Kade-HQ` and `G-Stack`
- Repo-owned richer runtime: `deps/pk-skills1`
- Packet-owned launcher wrappers: `skills/home/kade-hq`, `skills/home/g-kade`, `skills/home/gstack`
- Retrieval and embeddings plane: `pk-qmd`
- Durable memory plane: `Byterover` (`brv`)
- Graph and web plane: `GitVizz`

## Local Gateway

- Default local gateway: `127.0.0.1:8181`
- Routes:
  - `/mcp` -> `pk-qmd`
  - `/graph/*` -> GitVizz backend
  - `/memory/status`, `/memory/query`, `/memory/curate` -> narrow BRV adapter
- Auth rule:
  - loopback-only binds may run without auth
  - non-loopback binds must set `LLM_WIKI_AGENT_API_TOKEN`, unless an explicit unsafe override is set

## Setup Contract

- `scripts/setup_llm_wiki_memory.*` and `scripts/check_llm_wiki_memory.*` are thin wrappers
- Shared logic lives in `scripts/llm_wiki_memory_runtime.py`
- Managed installs prefer workspace or home `tooling.managed_tool_root` over global npm installs
- `pk-qmd` is pinned to commit `ef26cb62bb8132bc3a851b23f450af8e382e4c4e`

## Durable Memory Contract

- Official Obsidian vault name: `kade-hq`
- Official vault id: `fd8411f00d3a9d21`
- Official vault path: `C:\dev\Desktop-Projects\Helpful-Docs-Prompts\VAULTS-OBSIDIAN\Kade-HQ`
- Repo mirrors:
  - `AGENTS.md`
  - `.factory/memories.md`
  - `kade/AGENTS.md`
  - `kade/KADE.md`

## Source Of Truth

- Runtime config: `.llm-wiki/config.json`
- Canonical contract doc: `SYSTEM_CONTRACT.md`
- Operational backlog: `KNOWN_ISSUES.md`
