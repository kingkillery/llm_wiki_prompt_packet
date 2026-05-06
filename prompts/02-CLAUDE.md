# LLM Wiki Memory Claude Guide

Keep this file brief and directive.

## Startup

Before editing:

1. Read `.llm-wiki/config.json` if present.
2. Read `LLM_WIKI_MEMORY.md` if present.
3. Read `SKILL_CREATION_AT_EXPERT_LEVEL.md` if present when the task is about reusable skill authoring, review, or retirement.
4. If the stack is missing or inactive, run `.\scripts\setup_llm_wiki_memory.ps1` on Windows PowerShell or `./scripts/setup_llm_wiki_memory.sh` on shell-based systems before deeper work.
5. Read `wiki/index.md`.
6. Read recent `wiki/log.md`.
7. Search for existing related pages.

## Routing

- Use `pk-qmd` for repo-specific evidence and prompt or docs lookup.
- Use `pk-qmd` first when you still need to locate the right repo area.
- Use `pk-qmd` first when you still need to locate the right skill page or feedback history.
- Use Obsidian MCP tools for vault reads and writes when available.
- Before creating or accessing an Obsidian vault, confirm the vault path is established by `.llm-wiki/config.json`, MCP settings, environment variables, or current user instruction. If no vault path is established, ask the user where to create or access it. Do not silently use the current repo as an Obsidian vault.
- Proactively offer to save source-backed findings to Obsidian when they are likely to be useful later, especially research-paper notes, resolved investigations, durable decisions, and reusable procedures.
- Treat `agent-cli-obsidian` as the recommended Obsidian behavior layer for wiki save/query/autoresearch conventions; treat `mcpvault` or `mcp-obsidian` as the lower-level vault transport.
- Use `brv` only for durable memory and repeated workflow knowledge.
- If `pk-qmd` and `brv` disagree, trust current source evidence.
- If BRV has no connected provider, skip BRV query/curate and continue with source evidence.
- Treat `GitVizz` as the configured local graph surface.
- Use `GitVizz` when the task is about repo structure, API surface, dependency context, or narrowing around a known folder, route, or component.

## Rules

- Do not edit raw sources unless explicitly asked.
- If the user asks how to use this tool, what it can do, how to install it, how to save to the wiki, how to use Obsidian, or what command to run next, answer directly in plain language. `/wiki-help` is the optional shortcut, not a prerequisite.
- For install help, show exactly one command for the user's current shell unless they ask for alternatives.
- Update existing wiki pages before creating new ones.
- Good answers and insights should not disappear into chat history. After a substantial answer, especially research or analysis, offer to save it; for deep research, saving should be the default unless the user opts out.
- If Obsidian/wiki persistence would be useful but the vault path is unconfigured, ask for the vault location before saving.
- Use the Obsidian wiki note taxonomy: `synthesis`, `concept`, `source`, `decision`, and `session`; for research use source/entity/concept/question pages plus a synthesis page when useful.
- For research and investigation tasks, offer to write an Obsidian/wiki note that preserves the source citation, what was learned, why it mattered, caveats, and follow-up questions.
- Maintain links, contradictions, and open questions.
- Treat reusable skills as maintained assets with explicit lifecycle, feedback, and retirement.
- Keep edits small and reversible.

## Done

The task is complete only when relevant pages are updated, plus `index.md` and `log.md` when needed.
