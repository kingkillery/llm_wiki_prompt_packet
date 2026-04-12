---
name: g-kade
description: Use when the user wants the KADE plus gstack bridge, including session kickoff with user-profile context, /g-kade install style project scaffolding, repo adaptation, or structured handoff logging tied to llm-wiki-memory packet setup. This packet-owned wrapper is installable into ~/.agents/skills, ~/.codex/skills, and ~/.claude/skills.
---

# g-kade

This is the packet-owned bridge skill for KADE plus gstack.

Its only purpose is to unify `kade-hq` plus `gstack` and make routing easier for the agent.
It is not the KADE System itself and it is not proof that the richer upstream runtime is installed.

## Startup

1. Read repo-local instructions first.
2. Detect whether a richer external `g-kade` skill or full `gstack` bundle is installed.

A richer install is one that contains runtime or companion content beyond this wrapper, for example `bin/`, `browse/`, `qa/`, `review/`, `kade/`, or multiple sibling skill folders.

Check these locations in order:

- `C:\Users\prest\.agents\skills\g-kade`
- `C:\Users\prest\.agents\skills\gstack`
- `~/.codex/skills/g-kade`
- `~/.claude/skills/g-kade`
- `~/.agents/skills/g-kade`
- `~/.codex/skills/gstack`
- `~/.claude/skills/gstack`
- `~/.agents/skills/gstack`
- repo-local `.codex/skills/g-kade`
- repo-local `.claude/skills/g-kade`
- repo-local `.agents/skills/g-kade`
- repo-local `.codex/skills/gstack`
- repo-local `.claude/skills/gstack`
- repo-local `.agents/skills/gstack`

If you find a richer install, read the relevant upstream `SKILL.md` there and use it.

If you do not find one, continue with this wrapper.

## Install Flow

Use the current invoked folder as the workspace root unless deeper repo instructions say otherwise.

Fastest local path when the packet checkout is present:

- `python installers/install_g_kade_workspace.py --workspace <repo-root>`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\installers\install_g_kade_workspace.ps1 --workspace <repo-root>`
- `bash ./installers/install_g_kade_workspace.sh --workspace <repo-root>`

Hosted fallback when only the hosted installer is available:

- PowerShell:
  - `LLM_WIKI_INSTALL_MODE=g-kade`
  - then run the hosted `install.ps1` with the repo root path
- Shell:
  - `LLM_WIKI_INSTALL_MODE=g-kade`
  - then run the hosted `install.sh` with the repo root path

This flow must:

- detect the repo root from the invoked location
- install the packet into that repo root
- scaffold repo-local `g-kade` and `gstack` skill surfaces
- scaffold `kade/AGENTS.md` and `kade/KADE.md`
- run setup and health helpers with GitVizz skipped unless it is configured

After install, verify these surfaces:

- `AGENTS.md`
- `CLAUDE.md`
- `LLM_WIKI_MEMORY.md`
- `.llm-wiki/config.json`
- `scripts/setup_llm_wiki_memory.ps1` or `.sh`

For first-run setup, prefer the installed helper from the target vault:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_llm_wiki_memory.ps1`
- `bash ./scripts/setup_llm_wiki_memory.sh`

If GitVizz is not configured yet, do not block the packet install on it:

- leave `gitvizz.repo_path` unset until you have the GitVizz checkout
- use `-SkipGitvizz` or `--skip-gitvizz` when you want setup to focus on QMD, BRV, and MCP wiring first
- once the repo path is configured, use `scripts/launch_gitvizz.ps1` or `.sh` and then rerun setup or health checks

Scaffold or refresh these KADE overlays when missing or stale:

- `~/.kade/HUMAN.md`
- `kade/AGENTS.md`
- `kade/KADE.md`

Treat packet instructions as the base contract. Layer KADE guidance on top instead of replacing packet surfaces.

## Fastest Successful Install

1. Run `python installers/install_g_kade_workspace.py --workspace <repo-root>`.
2. Let it install the packet into the repo root.
3. Let it scaffold repo-local `.agents/.codex/.claude` skill surfaces for both `g-kade` and `gstack`.
4. Let it run `scripts/setup_llm_wiki_memory.ps1` or `.sh` with GitVizz skipped unless a real GitVizz repo path is configured.
5. Confirm the workspace has packet files, local skill files, and a valid health-helper path.

## Roadblocks And Corrections

- Roadblock: packet install alone stops at file copy.
  Correction: use the dedicated `install_g_kade_workspace.py` flow so install continues into repo-local scaffolding, setup, and health validation.
- Roadblock: home skill install can look successful while the current repo is still unbootstrapped.
  Correction: always target the repo root first and treat home skill installs as optional overlays, not proof of bootstrap.
- Roadblock: GitVizz may be unset during first-run bootstrap.
  Correction: run setup and health with `SkipGitvizz` / `--skip-gitvizz` so QMD, BRV, and MCP wiring happen first.
- Roadblock: thin packet wrappers can be mistaken for richer upstream runtimes.
  Correction: only treat an upstream install as richer when it contains runtime or companion content beyond the wrapper, such as `bin/`, `browse/`, `qa/`, `review/`, `kade/`, or multiple workflow folders.

## Wish I Knew Before Install

- `xyz`: a successful `/g-kade install` is not "copy the wrapper skill". It is "bootstrap the repo into a layered workspace".
- `xyz`: the repo root is the workspace target; `~/.agents/skills/g-kade` by itself is not enough.
- `xyz`: the fastest reliable path is the dedicated `install_g_kade_workspace.py` entrypoint because it already handles packet install, repo-local skill scaffolding, KADE overlays, setup, and verification in one place.

## Session Flow

- Read `~/.kade/HUMAN.md` when present.
- Read `kade/AGENTS.md` and the latest handoff in `kade/KADE.md` when present.
- Clarify the session goal, propose a short plan, and keep one next action visible.
- Route execution to the right workflow: investigate, review, QA, ship, design, docs, or deployment.
- End by appending a concise handoff entry with changed files, why, verification, and next action.

## Constraints

- Preserve the separation of concerns:
  - the packet owns search, memory, MCP wiring, and workspace scaffolding
  - KADE owns user profile, handoff state, and session structure
  - gstack-style workflows own execution tactics
- Do not claim the full upstream `g-kade` runtime is installed unless you verified it.
- Report whether you used this packet wrapper or a richer external install.
