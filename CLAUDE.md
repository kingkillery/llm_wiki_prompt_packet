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

## MCP Servers

This project wires four MCP servers via `.mcp.json`. Each is available as `mcp__<name>__<tool>`.

| Server | Transport | Purpose | Required? |
|--------|-----------|---------|----------|
| `pk-qmd` | stdio | Source evidence, docs, prompts, notes retrieval | **Always** |
| `llm-wiki-skills` | stdio | Skill lifecycle (lookup, reflect, validate, evolve, retire) | **Always** |
| `obsidian` | stdio (npx) | Vault read/write — the scribing surface for wiki notes | **Pivotal but optional** |

### Obsidian: pivotal but optional

The `obsidian` MCP server connects to the configured Obsidian vault and provides `read_note`, `write_note`, `search_notes`, `manage_tags`, and `move_note` tools. It is the **preferred path** for all wiki scribing — creating, updating, and organizing notes.

Vault path rule: if `.llm-wiki/config.json`, MCP settings, environment variables, or the current user instruction establishes the Obsidian vault path, use that. If no vault path is established, ask the user where to create or access the Obsidian vault before reading, writing, creating, or assuming any vault. Do not silently use the current repo as an Obsidian vault.

Offer Obsidian persistence whenever the answer produces reusable knowledge that would be expensive to rediscover. This includes research-paper summaries, source-backed findings, solved debugging trails, durable decisions, procedures, and anything the user may reasonably reference in a later related task. When the user agrees, save a compact note with citations/source links, key claims, caveats, open questions, and useful tags.

Use `agent-cli-obsidian` as the recommended Obsidian behavior layer for save/query/autoresearch conventions. Keep `mcpvault` or `mcp-obsidian` as the transport layer for actual vault reads and writes.

When `obsidian` is unavailable (desktop app not running, vault not mounted, MCP connection refused):

1. Fall back to direct file I/O only against the configured vault path.
2. Log that the fallback was used (append to `wiki/log.md`).
3. Note any link-integrity risk — Obsidian-aware moves preserve backlinks; raw file moves do not.
4. If the task is a rename or move, prefer pausing and asking the user to open Obsidian rather than risking broken links.

## Routing

- Use `pk-qmd` for repo-specific evidence and prompt or docs lookup.
- Use `pk-qmd` first when you still need to locate the right repo area.
- Use `pk-qmd` first when you still need to locate the right skill page or feedback history.
- Prefer code-mode or packet CLI/provider paths for vault reads and writes; use `obsidian` MCP only when it is already available and materially cheaper.
- Proactively offer to save source-backed findings to Obsidian when they are likely to be useful later, especially research-paper notes, resolved investigations, durable decisions, and reusable procedures.
- Treat `agent-cli-obsidian` as the recommended Obsidian behavior layer for wiki save/query/autoresearch conventions; treat `mcpvault` or `mcp-obsidian` as the lower-level vault transport.
- Treat `GitVizz` as the configured local graph surface.
- Use `GitVizz` when the task is about repo structure, API surface, dependency context, or narrowing around a known folder, route, or component.

## Active llm-wiki-skills Contract

`llm-wiki-skills` is active in a repo after the user has run the packet "wire up the harness" flow for that repo, such as `-WireRepo`, `--wire-repo`, `scripts/setup_llm_wiki_memory.*`, or `scripts/llm_wiki_packet.py init --project-root <repo>`. Active means repo-local agent instructions and `.llm-wiki/` scaffolding are intentionally installed; it does not mean an MCP server is running.

The comprehensive workflow, CLI/MCP usage, required fields, validation checks, feedback loop, and retirement rules are documented in `skills/home/llm-wiki-skills/SKILL.md`; read it before doing skill lifecycle work.

The active/inactive switch block, when present, is authoritative for whether lifecycle checks are required. If the switch says inactive, do not require skill lookup, capture, validation, feedback, or retirement steps unless the user explicitly asks.

Activation controls:

- `scripts/llm_wiki_packet.py enable` restores the packet-managed switch block and marks the harness active for the repo. Aliases: `start`, `new`.
- `scripts/llm_wiki_packet.py disable` leaves an inactive packet-managed switch block and marks the harness inactive without deleting the wiki, registry, logs, or user-authored notes. Aliases: `stop`, `quit`.
- `scripts/llm_wiki_packet.py status` reports the switch state and expected local files.

## Rules

- Do not edit raw sources unless explicitly asked.
- Update existing wiki pages before creating new ones.
- Prefer code-mode/direct file I/O or packet CLI/provider paths over `obsidian` MCP for vault mutations when the configured vault path is known.
- Good answers and insights should not disappear into chat history. After a substantial answer, especially research or analysis, offer to save it; for deep research, saving should be the default unless the user opts out.
- Use the Obsidian wiki note taxonomy: `synthesis`, `concept`, `source`, `decision`, and `session`; for research use source/entity/concept/question pages plus a synthesis page when useful.
- For research and investigation tasks, offer to write an Obsidian/wiki note that preserves the source citation, what was learned, why it mattered, caveats, and follow-up questions.
- When `obsidian` is unavailable, direct file I/O is acceptable but note the fallback in `wiki/log.md`.
- Maintain links, contradictions, and open questions.
- Treat reusable skills as maintained assets with explicit lifecycle, feedback, and retirement.
- Keep edits small and reversible.

## Done

The task is complete only when relevant wiki pages are updated, plus `index.md` and `log.md` when needed.
