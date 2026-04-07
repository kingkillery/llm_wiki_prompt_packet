# LLM Wiki Memory Claude Guide

Keep this file brief and directive.

## Startup

Before editing:

1. Read `.llm-wiki/config.json` if present.
2. Read `LLM_WIKI_MEMORY.md` if present.
3. If the stack is missing or inactive, run `.\scripts\setup_llm_wiki_memory.ps1` on Windows PowerShell or `./scripts/setup_llm_wiki_memory.sh` on shell-based systems before deeper work.
4. Read `wiki/index.md`.
5. Read recent `wiki/log.md`.
6. Search for existing related pages.

## Routing

- Use `pk-qmd` for repo-specific evidence and prompt or docs lookup.
- Use `pk-qmd` first when you still need to locate the right repo area.
- Use `brv` only for durable memory and repeated workflow knowledge.
- If `pk-qmd` and `brv` disagree, trust current source evidence.
- If BRV has no connected provider, skip BRV query/curate and continue with source evidence.
- Treat `GitVizz` as the configured local graph surface.
- Use `GitVizz` when the task is about repo structure, API surface, dependency context, or narrowing around a known folder, route, or component.

## Rules

- Do not edit raw sources unless explicitly asked.
- Update existing wiki pages before creating new ones.
- Maintain links, contradictions, and open questions.
- Keep edits small and reversible.

## Done

The task is complete only when relevant pages are updated, plus `index.md` and `log.md` when needed.
