# LLM Wiki Memory Agent Guide

Maintain this vault as a persistent markdown wiki built from immutable raw sources.

## Startup

Before substantive work:

1. Read this file.
2. Read `LLM_WIKI_MEMORY.md` if present.
3. Read `SKILL_CREATION_AT_EXPERT_LEVEL.md` if present when the task touches reusable skill authoring or review.
4. Read `.llm-wiki/config.json` if present.
5. If `pk-qmd`, `brv`, or GitVizz are missing, run the installed setup helper before deeper work:
   - PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_llm_wiki_memory.ps1`
   - Shell: `bash ./scripts/setup_llm_wiki_memory.sh`
6. Read `wiki/index.md`.
7. Read recent `wiki/log.md`.
8. Search for existing related pages.

## Tool routing

- Use `pk-qmd` for repo-specific source evidence.
- Use `pk-qmd` first when the target file, folder, prompt, or note is not yet known.
- Use `pk-qmd` first when the right existing skill page or feedback note is not yet known.
- Use `brv` only for durable preferences, decisions, and workflow quirks.
- Prefer current source evidence over `brv` memory when they conflict.
- If BRV has no connected provider, do not rely on `brv query` or `brv curate` for task completion.
- Use configured `GitVizz` URLs for local graph and web access.
- Use `GitVizz` when you need repo topology, API surface, route relationships, or to hone in after `pk-qmd` found the likely area.
- Do not surface raw tool choices to end users unless asked.

## Rules

- Never edit `raw/` unless explicitly asked.
- Prefer updating existing pages over creating duplicates.
- Maintain links, contradictions, and open questions.
- Treat reusable skills as first-class wiki artifacts, not ad hoc notes.
- Make small, reversible edits by default.
- Ask before deletions, large renames, or restructures.

## Done when

A task is complete only when relevant pages are updated, `index.md` is updated if needed, and `log.md` is updated if needed.
