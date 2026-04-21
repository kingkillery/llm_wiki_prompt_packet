Read `CLAUDE.md`, then read `LLM_WIKI_MEMORY.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, and the most relevant wiki pages first.

Answer the user's question from the wiki. Read raw sources only when needed.
If the result is durable, file it back into the wiki, then update `wiki/index.md` and append a `query` entry to `wiki/log.md`.

Routing:
- use `pk-qmd` MCP tools for repo-specific evidence and prompt lookup
- use `pk-qmd` first when the right folder, file, or prompt is not known yet
- use `obsidian` MCP tools (`read_note`, `write_note`, `search_notes`) for vault reads and writes when available; fall back to direct file I/O if `obsidian` is down
- use `GitVizz` when repo topology, API routes, or dependency context will help narrow or explain the answer
- use `brv` for durable preferences, prior decisions, or repeated workflow quirks
- if `pk-qmd` and `brv` conflict, answer from current source evidence

Return:
- stack/config used
- MCP tools used (or fallback note if `obsidian` was unavailable)
- files read
- files changed
- unresolved conflicts
- next best actions
