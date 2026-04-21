# LLM Wiki Memory Claude Guide

Keep this file brief and directive.

## Startup

Before editing:

1. Read `.llm-wiki/config.json` if present.
2. Read `LLM_WIKI_MEMORY.md` if present.
3. Read `SKILL_CREATION_AT_EXPERT_LEVEL.md` if present when the task is about reusable skill authoring, review, or retirement.
4. If the stack is missing or inactive, run `.\scripts\setup_llm_wiki_memory.ps1` on Windows PowerShell or `./scripts/setup_llm_wiki_memory.sh` on shell-based systems before deeper work.
5. Read `wiki/index.md`.
6. Read recent `wiki/log.md`.
7. Search for existing related pages.

## MCP Servers

This project wires four MCP servers via `.mcp.json`. Each is available as `mcp__<name>__<tool>`.

| Server | Transport | Purpose | Required? |
|--------|-----------|---------|----------|
| `pk-qmd` | stdio | Source evidence, docs, prompts, notes retrieval | **Always** |
| `llm-wiki-skills` | stdio | Skill lifecycle (lookup, reflect, validate, evolve, retire) | **Always** |
| `obsidian` | stdio (npx) | Vault read/write — the scribing surface for wiki notes | **Pivotal but optional** |
| `brv` | stdio | Durable memory, preferences, workflow quirks | Optional |

### Obsidian: pivotal but optional

The `obsidian` MCP server connects to the Kade-HQ vault and provides `read_note`, `write_note`, `search_notes`, `manage_tags`, and `move_note` tools. It is the **preferred path** for all wiki scribing — creating, updating, and organizing notes.

When `obsidian` is unavailable (desktop app not running, vault not mounted, MCP connection refused):

1. Fall back to direct file I/O against the vault path.
2. Log that the fallback was used (append to `wiki/log.md`).
3. Note any link-integrity risk — Obsidian-aware moves preserve backlinks; raw file moves do not.
4. If the task is a rename or move, prefer pausing and asking the user to open Obsidian rather than risking broken links.

### BRV: skip gracefully

If `brv` has no connected provider, skip `brv query`/`brv curate` and continue with source evidence from `pk-qmd`.

## Routing

- Use `pk-qmd` for repo-specific evidence and prompt or docs lookup.
- Use `pk-qmd` first when you still need to locate the right repo area.
- Use `pk-qmd` first when you still need to locate the right skill page or feedback history.
- Use `obsidian` MCP tools for all vault reads and writes when available.
- Use `brv` only for durable memory and repeated workflow knowledge.
- If `pk-qmd` and `brv` disagree, trust current source evidence.
- If BRV has no connected provider, skip BRV query/curate and continue with source evidence.
- Treat `GitVizz` as the configured local graph surface.
- Use `GitVizz` when the task is about repo structure, API surface, dependency context, or narrowing around a known folder, route, or component.

## Rules

- Do not edit raw sources unless explicitly asked.
- Update existing wiki pages before creating new ones.
- Prefer `obsidian` MCP tools over direct file I/O for vault mutations.
- When `obsidian` is unavailable, direct file I/O is acceptable but note the fallback in `wiki/log.md`.
- Maintain links, contradictions, and open questions.
- Treat reusable skills as maintained assets with explicit lifecycle, feedback, and retirement.
- Keep edits small and reversible.

## Done

The task is complete only when relevant wiki pages are updated, plus `index.md` and `log.md` when needed.
