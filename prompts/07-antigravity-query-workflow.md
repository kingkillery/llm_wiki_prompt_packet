---
description: answer from the persistent wiki and file durable outputs back into the obsidian vault
---
# Wiki query workflow

1. Read `AGENTS.md` if present.
2. Read `wiki/index.md`.
3. Read the most relevant wiki pages first.
4. Consult raw sources only when needed.
5. Answer the question with grounding.
6. If the answer is durable, create or update the relevant wiki page.
7. Update `wiki/index.md` if needed.
8. Append a `query` entry to `wiki/log.md` if a durable page was filed.
9. Return:
   - files read
   - files changed
   - unresolved conflicts
   - next best actions
