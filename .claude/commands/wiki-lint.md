---
description: lint and maintain the persistent wiki
allowed-tools:
  - "mcp__pk-qmd__*"
  - "mcp__obsidian__read_note"
  - "mcp__obsidian__write_note"
  - "mcp__obsidian__search_notes"
  - "mcp__obsidian__manage_tags"
  - "mcp__obsidian__move_note"
  - "mcp__llm-wiki-skills__skill_lookup"
  - "mcp__llm-wiki-skills__skill_validate"
  - "mcp__brv__*"
---
Read `CLAUDE.md`, `LLM_WIKI_MEMORY.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, and recent `wiki/log.md`.

Lint the wiki for:
- contradictions
- stale claims
- orphan or weakly linked pages
- duplicate pages
- broken links
- missing entity or concept pages
- obvious research gaps
- stack-routing rules that are missing or unclear

Fix safe issues directly. Prefer `obsidian` MCP tools for vault mutations when available.
For renames and moves, always prefer `obsidian` `move_note` over direct file I/O to preserve link integrity.
If `obsidian` is unavailable, log the fallback in `wiki/log.md` and flag link-integrity risk.
Flag judgment-heavy recommendations separately.
Update `wiki/index.md` if needed and append a `lint` entry to `wiki/log.md`.

Return:
- stack/config used
- MCP tools used (or fallback note if `obsidian` was unavailable)
- files changed
- issues fixed
- issues deferred
- next best actions
