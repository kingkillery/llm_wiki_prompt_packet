---
description: ingest a single source into the persistent wiki
allowed-tools:
  - "mcp__pk-qmd__*"
  - "mcp__obsidian__read_note"
  - "mcp__obsidian__write_note"
  - "mcp__obsidian__search_notes"
  - "mcp__obsidian__manage_tags"
  - "mcp__llm-wiki-skills__skill_lookup"
  - "mcp__brv__*"
---
Read `CLAUDE.md`, then read `LLM_WIKI_MEMORY.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, and recent `wiki/log.md`.

Ingest the specified source into the wiki:
- create or update a source summary
- update affected entity, concept, synthesis, comparison, or timeline pages
- update `wiki/index.md`
- append an `ingest` entry to `wiki/log.md`

## Retrieval Protocol (apply before every search)

**Step 0 — Context gate:** Check `wiki/index.md` and recently read log entries first. If existing wiki pages clearly cover this source's topic area, go directly to those pages. Do not fire `pk-qmd` just to confirm what `wiki/index.md` already shows.

**Step 1 — Classify need:**
- Known topic, existing page → read page directly, update it. No retrieval needed.
- Partially known topic → `pk-qmd` lex to find closely related pages. One call.
- Novel topic, broad evidence needed → `pk-qmd` lex + vec. Cap at 2 hops for page discovery.

**Step 2 — Iterate at most twice** for page discovery. If the second hop overlaps >50% with the first, stop.

**Step 3 — brv:** Only consult for stable workflow preferences that affect how to classify or file the source. Skip gracefully if no provider is connected.

## Routing

- use `pk-qmd` MCP tools for repo-specific evidence retrieval if needed
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
