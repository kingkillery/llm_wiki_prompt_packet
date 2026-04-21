---
description: answer from the wiki and file durable results
allowed-tools:
  - "mcp__pk-qmd__*"
  - "mcp__obsidian__read_note"
  - "mcp__obsidian__search_notes"
  - "mcp__obsidian__write_note"
  - "mcp__obsidian__manage_tags"
  - "mcp__llm-wiki-skills__skill_lookup"
  - "mcp__brv__*"
---
Read `CLAUDE.md`, then read `LLM_WIKI_MEMORY.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, and the most relevant wiki pages first.

## Retrieval Protocol (apply before every search)

**Step 0 — Context gate:** Check if the answer is already available in loaded context (wiki/index.md, recent wiki/log.md entries, or prior conversation). If yes, answer directly without retrieving.

**Step 1 — Classify complexity:**
- Single fact / preference / prior decision → CHEAP tier
- Semantic / conceptual / multi-source → STANDARD tier
- Multi-hop / structural / synthesis → FULL tier

**Step 2 — Execute by tier (hard cap: 3 retrieval iterations total):**
- CHEAP: `brv` query only. If miss, escalate to STANDARD.
- STANDARD: `pk-qmd` (lex + vec). Run `brv` in parallel if brv is relevant to the query and its result does not need to inform the pk-qmd query.
- FULL: `pk-qmd` (lex + vec + hyde) + `brv` parallel. Add GitVizz only if query is about repo structure, API surface, or dependency relationships.

**Step 3 — Before each hop after the first:** Check if new results overlap >50% with prior results. If yes, stop — the query has converged. Answer from current best evidence.

**Step 4 — Deduplicate:** Before passing chunks to generation, remove any chunk already seen in this query session. Replace with the next-ranked result.

**Skip brv gracefully** if no provider is connected — do not error, continue with pk-qmd.

## Routing after retrieval

- use `pk-qmd` MCP tools for repo-specific evidence and prompt lookup
- use `pk-qmd` first when the target repo area is not yet known
- use `obsidian` MCP tools (`read_note`, `write_note`, `search_notes`) for vault reads and writes when available; fall back to direct file I/O if `obsidian` is down
- use `GitVizz` when repo structure, API context, or dependency relationships are the real need
- use `brv` for durable preferences, prior decisions, or repeated workflow quirks
- if `pk-qmd` and `brv` conflict, answer from current source evidence

## Filing results

If the result is durable, file it back into the wiki, then update `wiki/index.md` and append an entry to `wiki/log.md`.

## Return format

- stack/config used
- MCP tools used (or fallback note if `obsidian` was unavailable)
- files read
- files changed
- unresolved conflicts
- next best actions
