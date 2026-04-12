# AGENTS.md

This `kade/AGENTS.md` file is the KADE overlay for this packet-backed workspace.

Load order:

- `~/.kade/HUMAN.md` when present
- repo root `AGENTS.md`
- repo root `.factory/memories.md`
- repo root `.llm-wiki/config.json` when present
- this file
- `kade/KADE.md`

Boundaries:

- root packet files own search, memory, MCP wiring, Docker gateway behavior, and workspace scaffolding
- this overlay owns project-local KADE session context and handoff alignment
- richer `g-kade` and `gstack` runtimes belong in repo-owned dependency paths, not home wrappers alone
- do not overwrite root packet files with KADE-specific content

Repo runtime contract:

- `g-kade`: `detected` at `deps/pk-skills1/gstack/g-kade`
- `gstack`: `detected` at `deps/pk-skills1/gstack`
- launcher wrappers: `skills/home/g-kade` and `skills/home/gstack`
- local Docker gateway: `127.0.0.1:8181` with `/mcp`, `/graph/*`, and `/memory/*`
- local Docker auth: none on loopback-only binds; hosted paths must add auth

Workspace root: `C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet`
