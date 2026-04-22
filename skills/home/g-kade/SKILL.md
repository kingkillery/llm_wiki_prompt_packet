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

### One-command hosted install (`--wire-repo`)

Preferred path. Works from any directory. Downloads the latest release, installs the packet, wires global Claude config, and runs the health check as the closing step.

**PowerShell (Windows):**
```powershell
$f="$env:TEMP\llm-wiki-install.ps1"; iwr https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1 -OutFile $f; & $f -WireRepo
```

**Shell (macOS / Linux):**
```bash
curl -fsSL https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.sh | bash -s -- --wire-repo
```

The health check propagates its exit code so chained commands honor failure.
Set `LLM_WIKI_HEALTH_CHECK_NONFATAL=1` to restore warn-only behavior.

### Local checkout install

When the `llm_wiki_prompt_packet` checkout is already on disk:

- `bash ./install.sh --wire-repo` (from inside the checkout, wires current directory)
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -WireRepo`
- `python installers/install_g_kade_workspace.py --workspace <repo-root>`
- `bash ./installers/install_g_kade_workspace.sh --workspace <repo-root>`

### Legacy packet CLI (still supported)

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\support\scripts\llm_wiki_packet.ps1 init --project-root <repo-root>`
- `python .\support\scripts\llm_wiki_packet.py init --project-root <repo-root>`

Prefer `--wire-repo` for new setups. The legacy CLI delegates to the same workspace installer but does not run the closing health check or global Claude wiring by default.

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

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\llm_wiki_packet.ps1 setup`
- `python .\scripts\llm_wiki_packet.py setup`
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

1. Run `bash ./install.sh --wire-repo` (or `install.ps1 -WireRepo` on Windows) from inside the target repo.
2. It runs preflight, installs the packet, scaffolds repo-local `.agents/.codex/.claude` skill surfaces for `kade-hq`, `g-kade`, `gstack`, and `pokemon-benchmark`.
3. It wires global Claude config (`~/.claude/CLAUDE.md` + `~/.claude/commands/wiki-*.md`).
4. It runs the health check and propagates exit code (set `LLM_WIKI_HEALTH_CHECK_NONFATAL=1` for warn-only).
5. Confirm the workspace has packet files, local skill files, and a passing health check.

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

- `xyz`: a successful install is not "copy the wrapper skill". It is "bootstrap the repo into a layered workspace". Use `--wire-repo` for the full one-command path.
- `xyz`: the repo root is the workspace target; `~/.agents/skills/g-kade` by itself is not enough.
- `xyz`: `--wire-repo` is the fastest reliable path because it handles preflight, install, global Claude wiring, and health check in one step.
- `xyz`: the health check exit code propagates by default. Set `LLM_WIKI_HEALTH_CHECK_NONFATAL=1` if your automation needs warn-only behavior.

## Session Flow

- Read `~/.kade/HUMAN.md` when present.
- Read `kade/AGENTS.md` and the latest handoff in `kade/KADE.md` when present.
- Clarify the session goal, propose a short plan, and keep one next action visible.
- Route execution to the right workflow: investigate, review, QA, ship, design, docs, or deployment.
- End by appending a concise handoff entry with changed files, why, verification, and next action.

## Simple memory routing

Keep the bridge easy to reason about:

- `HUMAN.md` = personal layer
- `kade/KADE.md` = episodic session layer
- `wiki/` = semantic repo layer
- `wiki/skills/active/` = procedural shortcut layer
- `brv` = durable preference layer

When in doubt, summarize upward instead of copying raw detail forward.

## Constraints

- Preserve the separation of concerns:
  - the packet owns search, memory, MCP wiring, and workspace scaffolding
  - KADE owns user profile, handoff state, and session structure
  - gstack-style workflows own execution tactics
- Abstract and simplify while maintaining the Kade homage.
- Do not claim the full upstream `g-kade` runtime is installed unless you verified it.
- Report whether you used this packet wrapper or a richer external install.
