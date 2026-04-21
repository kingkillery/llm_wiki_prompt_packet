---
name: llm-wiki-organizer
description: Use this skill when the repo is an llm-wiki-memory vault and the task is to ingest a source, answer from the persistent wiki, use pk-qmd for repo-local evidence retrieval, consult brv for durable memory, or lint and maintain the wiki.
---

# LLM Wiki Memory Organizer

This skill helps maintain a persistent markdown wiki backed by an explicit retrieval and memory stack.

## Startup

1. Read `AGENTS.md`.
2. Read `LLM_WIKI_MEMORY.md` if present.
3. Read `.llm-wiki/config.json` if present.
4. If `pk-qmd`, `brv`, or GitVizz are not ready, run `scripts/setup_llm_wiki_memory.ps1` or `scripts/setup_llm_wiki_memory.sh` before substantive work.
5. Read `wiki/index.md`.
6. Read recent `wiki/log.md`.
7. Search for existing pages before creating new ones.

## MCP Servers

Four MCP servers are wired via `.mcp.json`:

| Server | Purpose | Required? |
|--------|---------|----------|
| `pk-qmd` | Source evidence retrieval | **Always** |
| `llm-wiki-skills` | Skill lifecycle (lookup, reflect, validate, evolve, retire) | **Always** |
| `obsidian` | Vault read/write — wiki scribing surface | **Pivotal but optional** |
| `brv` | Durable memory, preferences, workflow quirks | Optional |

### Obsidian: pivotal but optional

The `obsidian` MCP server connects to the Kade-HQ vault and provides `read_note`, `write_note`, `search_notes`, `manage_tags`, and `move_note` tools. It is the **preferred path** for all wiki scribing.

When `obsidian` is unavailable:
1. Fall back to direct file I/O against the vault path.
2. Log the fallback in `wiki/log.md`.
3. For renames and moves, prefer pausing and asking the user to open Obsidian rather than risking broken links.

### BRV: skip gracefully

If `brv` has no connected provider, skip `brv query`/`brv curate` and continue with source evidence.

## Routing

- `pk-qmd` is the default evidence lookup tool for repo-specific work.
- Use `pk-qmd` first for difficult searches when the target repo area is not known yet.
- Prefer `obsidian` MCP tools for all vault reads and writes when available.
- `brv` is for durable preferences, prior decisions, and costly rediscoveries.
- If BRV has no connected provider, do not block on BRV query/curate.
- `GitVizz` is the local graph and web surface.
- Use `GitVizz` to inspect repo topology, API routes, dependency context, and to narrow in once `pk-qmd` has located the relevant area.
- Source evidence beats memory for current factual claims.

## Response shape

- Task type
- Stack/config used
- MCP tools used (or fallback note if `obsidian` was unavailable)
- Files read
- Files changed
- What changed
- Unresolved questions or conflicts

## Skill pack resources

These files live alongside this skill in `assets/` and provide worked examples, evaluation criteria, failure-pattern guidance, decision tables, checklists, and a versioned improvement log.

- `EXAMPLES.md` — Worked examples for ingest, query, lint, conflict resolution, and multi-tool routing.
- `EVALS.md` — Pass/fail evaluation criteria for grading skill runs (task classification, routing, dedup, contract completeness).
- `FAILURE_MODES.md` — Known failure patterns with symptoms, root causes, detection, prevention, and recovery.
- `DECISION_RULES.md` — Condensed routing decision table, task classification rules, and evidence hierarchy.
- `CHECKLISTS.md` — Preflight startup checklist and exit checklist with task-specific additions.
- `PROCESS_IMPROVEMENTS.md` — Append-only log of approved behavioral changes with validation notes.
