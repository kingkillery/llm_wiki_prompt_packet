# Tool Directives

- Read schema and guide docs first.
- Read `LLM_WIKI_MEMORY.md` when present before tool setup or retrieval work.
- Read `.llm-wiki/config.json` before substantive retrieval work.
- If the stack is missing, run `scripts/setup_llm_wiki_memory.ps1` or `scripts/setup_llm_wiki_memory.sh` before deeper work.
- Read `wiki/index.md` and recent `wiki/log.md` before substantive work.
- Search before creating.

## MCP tool routing

Four MCP servers are wired via `.mcp.json`:

| Server | Purpose | Required? |
|--------|---------|----------|
| `pk-qmd` | Source evidence retrieval | **Always** |
| `llm-wiki-skills` | Skill lifecycle management | **Always** |
| `obsidian` | Vault read/write — wiki scribing | **Pivotal but optional** |
| `brv` | Durable memory, preferences | Optional |

### Obsidian: pivotal but optional

- Prefer `obsidian` MCP tools (`read_note`, `write_note`, `search_notes`, `manage_tags`, `move_note`) for all vault mutations.
- When `obsidian` is unavailable, fall back to direct file I/O.
- Log the fallback in `wiki/log.md`.
- For renames and moves, prefer pausing and asking the user to open Obsidian rather than risking broken links.

### BRV: skip gracefully

- If `brv` has no connected provider, do not block on BRV query/curate.

### General rules

- Use `pk-qmd` for repo-specific evidence retrieval.
- Use `pk-qmd` first when the right repo area is not yet known.
- Use `GitVizz` for repo topology, API/context discovery, and narrowing from a known folder or route.
- Use `brv` only for durable memory and repeated workflow knowledge.
- Prefer source evidence over memory when they conflict.
- Never edit `raw/` unless explicitly asked.
- Prefer targeted edits.
- Avoid duplicate pages.
- Ask before destructive or high-blast-radius changes.
