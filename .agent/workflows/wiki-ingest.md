Read `CLAUDE.md`, then read `LLM_WIKI_MEMORY.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, and recent `wiki/log.md`.

Ingest the specified source into the wiki:
- create or update a source summary
- update affected entity, concept, synthesis, comparison, or timeline pages
- update `wiki/index.md`
- append an `ingest` entry to `wiki/log.md`

Routing:
- use `pk-qmd` MCP tools for repo-specific evidence retrieval if the source is not already in scope
- use `obsidian` MCP tools (`read_note`, `write_note`, `search_notes`) for vault reads and writes when available; fall back to direct file I/O if `obsidian` is down
- use `brv` only for stable workflow or preference context
- trust current source evidence over memory

Return:
- stack/config used
- MCP tools used (or fallback note if `obsidian` was unavailable)
- files read
- files changed
- what changed
- unresolved questions
