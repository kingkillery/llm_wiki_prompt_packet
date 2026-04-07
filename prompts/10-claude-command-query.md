---
description: answer from the wiki and file durable results
---
Read `CLAUDE.md`, then read `LLM_WIKI_MEMORY.md` if present, `.llm-wiki/config.json`, `wiki/index.md`, and the most relevant wiki pages first.

Answer the user's question from the wiki. Read raw sources only when needed.
If the result is durable, file it back into the wiki, then update `wiki/index.md` and append a `query` entry to `wiki/log.md`.

Routing:
- use `pk-qmd` for repo-specific evidence and prompt lookup
- use `pk-qmd` first when the target repo area is not known yet
- use `GitVizz` when repo structure, API context, or dependency relationships are the real need
- use `brv` for durable preferences, prior decisions, or repeated workflow quirks
- if `pk-qmd` and `brv` conflict, answer from current source evidence

Return:
- stack/config used
- files read
- files changed
- unresolved conflicts
- next best actions
