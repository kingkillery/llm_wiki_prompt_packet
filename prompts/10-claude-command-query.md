---
description: answer from the wiki and file durable results
---
Read `CLAUDE.md`, then read `wiki/index.md` and the most relevant wiki pages first.

Answer the user's question from the wiki. Read raw sources only when needed.
If the result is durable, file it back into the wiki, then update `wiki/index.md` and append a `query` entry to `wiki/log.md`.

Rules:
- do not edit raw sources unless explicitly asked
- prefer concise, reusable wiki pages
- preserve ambiguity where the evidence is mixed

Return:
- files read
- files changed
- unresolved conflicts
- next best actions
