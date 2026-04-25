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

<!-- llm-wiki-prompt-packet:agents-guidance:start -->
## KADE-HQ, Memory, and Retrieval Routing

Use this workspace as a KADE-HQ-backed memory workspace. Treat `AGENTS.md`, `LLM_WIKI_MEMORY.md`, `.llm-wiki/config.json`, `wiki/`, and `kade/` as the operating contract for future agent work.

### Startup Routing

- Read `AGENTS.md` first, then `LLM_WIKI_MEMORY.md`, then `.llm-wiki/config.json` before substantive work.
- If this is a KADE-enabled workspace, also read `kade/AGENTS.md` and `kade/KADE.md` when present.
- Load `~/.kade/HUMAN.md` when present for user/workflow preferences, but prefer project-local instructions when they conflict.
- Run `scripts/setup_llm_wiki_memory.ps1` or `scripts/setup_llm_wiki_memory.sh` if required memory/retrieval tools are missing.

### Retrieval Order

- Use `pk-qmd` first for source-backed repo, prompt, note, and wiki evidence when the right file or concept is not already known.
- Use Obsidian MCP tools for wiki note reads, writes, moves, and tag updates when available; fall back to direct file I/O only when Obsidian is unavailable, and record that fallback in `wiki/log.md`.
- Use `llm-wiki-skills` for reusable skill lookup, reflection, validation, evolution, and retirement.
- Use BRV only for durable preferences, repeated workflow quirks, and decisions; do not rely on it when no provider is connected.
- Use GitVizz for repo topology, API surface, route relationships, and graph-oriented navigation after retrieval has identified the likely area.
- Prefer current source evidence over memory when sources and memory conflict.
- Start with `llm-wiki-packet context --task "..."` for a compact task bundle; use `llm-wiki-packet evidence --query "..."` or `llm-wiki-packet context --mode deep` only when broader hybrid/source search is useful.

### KADE-HQ System Use

- Treat KADE-HQ as the human/profile and workspace-orchestration layer, not as a replacement for project instructions.
- Treat `g-kade` as the bridge/router across KADE-HQ, G-Stack workflows, and this packet.
- Use G-Stack workflows for review, QA, debugging, browser dogfooding, deployment verification, and ship-readiness checks when the corresponding skill/runtime is installed.
- Keep the root packet files as the source of truth for memory/retrieval wiring; keep KADE-specific handoff state under `kade/`.

### Memory Writes

- Write durable repo knowledge to `wiki/` pages, not chat-only memory.
- Write reusable procedures as skill artifacts under the configured skill lifecycle, not ad hoc notes.
- Keep raw immutable sources under `raw/`; never edit `raw/` unless explicitly asked.
- Update `wiki/index.md` when adding or moving durable pages.
- Update `wiki/log.md` for meaningful wiki changes, tool fallbacks, setup changes, and unresolved questions.
- For long-running harness work, use `llm-wiki-packet manifest`, `reduce`, `evaluate`, `promote`, and `improve` so artifacts, memory promotion, and self-improvement gates share the same run id.
<!-- llm-wiki-prompt-packet:agents-guidance:end -->

## Done when

A task is complete only when relevant pages are updated, `index.md` is updated if needed, and `log.md` is updated if needed.
