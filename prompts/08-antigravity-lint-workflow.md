---
description: lint and maintain the persistent obsidian wiki
---
# Wiki lint workflow

1. Read `AGENTS.md` if present.
2. Read `wiki/index.md`.
3. Read recent `wiki/log.md`.
4. Check for:
   - contradictions
   - stale claims
   - orphan or weakly linked pages
   - duplicate pages
   - broken links
   - missing concept or entity pages
   - obvious research gaps
5. Fix safe issues directly.
6. Flag judgment-heavy recommendations separately.
7. Update `wiki/index.md` if page status changed.
8. Append a `lint` entry to `wiki/log.md`.
9. Return:
   - files changed
   - issues fixed
   - issues deferred
   - next best actions
