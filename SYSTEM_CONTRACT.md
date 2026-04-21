# System Contract

This repo packages the combined `Kade-HQ` + `G-Stack` + `pk-qmd` + `Byterover` + `GitVizz` system.

## Canonical Layers

- Harness layer: `Kade-HQ` and `G-Stack`
- Repo-owned richer runtime: `deps/pk-skills1`
- Packet-owned launcher wrappers: `skills/home/kade-hq`, `skills/home/g-kade`, `skills/home/gstack`, `skills/home/llm-wiki-skills`
- Retrieval and embeddings plane: `pk-qmd`
- Durable memory plane: `Byterover` (`brv`)
- Graph and web plane: `GitVizz`
- Vault scribing plane: `obsidian` MCP (pivotal but optional)

## MCP Servers (stdio via `.mcp.json`)

Four MCP servers are configured for direct agent access without Docker:

| Server | Command | Purpose | Required? |
|--------|---------|---------|----------|
| `pk-qmd` | `pk-qmd mcp` | Source evidence retrieval, docs, prompts, notes | **Always** |
| `llm-wiki-skills` | `python llm_wiki_skill_mcp.py mcp` | Skill lifecycle (lookup, reflect, validate, evolve, retire) | **Always** |
| `obsidian` | `npx -y @bitbonsai/mcpvault <vault-path>` | Vault read/write — wiki scribing surface | **Pivotal but optional** |
| `brv` | `brv mcp` | Durable memory, preferences, workflow quirks | Optional |

### Obsidian: pivotal but optional

The `obsidian` MCP server provides `read_note`, `write_note`, `search_notes`, `manage_tags`, and `move_note` tools against the Kade-HQ vault. It is the preferred path for all wiki mutations.

When `obsidian` is unavailable:
1. Fall back to direct file I/O against the vault path.
2. Log the fallback in `wiki/log.md`.
3. For renames and moves, prefer pausing and asking the user to open Obsidian (link-integrity risk).
4. The system remains fully functional — `pk-qmd` and `llm-wiki-skills` provide evidence and skill management independently.

### BRV: skip gracefully

When `brv` has no connected provider, skip `brv query`/`brv curate` and continue with source evidence from `pk-qmd`.

## Local Gateway (Docker / HTTP)

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

### Memory layer mapping

- Working memory: active prompt context + guide files
- Episodic memory: `.llm-wiki/skill-pipeline/briefs/` and `.llm-wiki/skill-pipeline/packets/`
- Semantic memory: `wiki/` knowledge pages
- Procedural memory: `wiki/skills/active/`
- Preference memory: `brv`

Active skills should be maintained as typed memory objects with memory scope, memory strategy, update strategy, durable facts, and provenance refs.

## Source Of Truth

- Runtime config: `.llm-wiki/config.json`
- MCP wiring: `.mcp.json`
- Canonical contract doc: `SYSTEM_CONTRACT.md`
- Operational backlog: `KNOWN_ISSUES.md`
