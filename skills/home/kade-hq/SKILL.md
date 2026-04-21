---
name: kade-hq
description: Use when the user wants the KADE System itself, including Layer 1 and Layer 2 context loading, KADE session structure, HUMAN.md and kade/ overlays, or project initialization and handoff workflows. This packet-owned wrapper is installable into ~/.agents/skills, ~/.codex/skills, and ~/.claude/skills.
---

# kade-hq

This is the packet-owned launcher wrapper for `kade-hq`.

`g-kade` is the bridge skill that coordinates `kade-hq` plus `gstack`.
Use `kade-hq` when the task is specifically about KADE context, profiles, overlays, or session flow.

## Startup

1. Read repo-local instructions first.
2. Detect whether a richer external `kade-hq` or `kade-headquarters` skill is installed.

A richer install is one that contains runtime or companion content beyond this wrapper, for example `templates/`, `references/`, `scripts/`, `HUMAN.md`, or multiple sibling support folders.

Check these locations in order:

- `~/.codex/skills/kade-hq`
- `~/.claude/skills/kade-hq`
- `~/.agents/skills/kade-hq`
- `~/.codex/skills/kade-headquarters`
- `~/.claude/skills/kade-headquarters`
- `~/.agents/skills/kade-headquarters`
- repo-local `.codex/skills/kade-hq`
- repo-local `.claude/skills/kade-hq`
- repo-local `.agents/skills/kade-hq`
- repo-local `.codex/skills/kade-headquarters`
- repo-local `.claude/skills/kade-headquarters`
- repo-local `.agents/skills/kade-headquarters`

If you find a richer install, read the upstream `SKILL.md` there and use it.

If you do not find one, continue with this wrapper.

## Packet Integration

Keep the layering simple and recognizable:

- Treat `~/.kade/HUMAN.md` as **Layer 1**: who Kade is, preferences, style, and personal operating context.
- Treat `kade/AGENTS.md` and `kade/KADE.md` as **Layer 2**: the project-local Kade overlay and handoff surface.
- Treat the root packet files and `.llm-wiki/config.json` as **Layer 3**: workspace contract, search, memory, and MCP wiring.
- Treat `g-kade` as the unifier surface and `gstack` as the execution-workflow surface.

When knowledge needs to persist:

- put session/handoff context in `kade/KADE.md`
- put reusable procedural shortcuts in `llm-wiki-skills`
- put stable repo knowledge in `wiki/`

This keeps the Kade homage intact: human layer first, project layer second, harness layer third.

## Install Flow

When bootstrapping a repo workspace, prefer:

- `python installers/install_g_kade_workspace.py --workspace <repo-root>`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\installers\install_g_kade_workspace.ps1 --workspace <repo-root>`
- `bash ./installers/install_g_kade_workspace.sh --workspace <repo-root>`

This flow should leave these KADE surfaces in place:

- `~/.kade/HUMAN.md`
- `kade/AGENTS.md`
- `kade/KADE.md`
- repo-local `kade-hq`, `gstack`, and `g-kade` skill surfaces

## Constraints

- Abstract and simplify by default; do not overcomplicate the KADE layers with unnecessary mechanism names in user-facing explanations.
- Preserve the Kade homage: keep the human/profile layer legible and first-class.
- Do not treat `g-kade` as a replacement for `kade-hq`; it is only the bridge skill.
- Preserve a real existing `~/.kade/HUMAN.md`; only seed or replace the exact legacy stub.
- Report whether you used this wrapper or a richer external `kade-hq` install.
