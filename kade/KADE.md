# KADE.md

## Workspace

- root: `C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet`
- layering result: `repo-local intentional memory loop active`

## Repo Runtime Contract

- official Obsidian memory base: `C:\dev\Desktop-Projects\Helpful-Docs-Prompts\VAULTS-OBSIDIAN\Kade-HQ\llm_wiki_prompt_packet System Map.md`
- official vault identity: `kade-hq` / `fd8411f00d3a9d21`
- `g-kade`: status `detected`, configured `deps/pk-skills1/gstack/g-kade`
- `gstack`: status `detected`, configured `deps/pk-skills1/gstack`
- launcher wrappers: `skills/home/kade-hq`, `skills/home/g-kade`, and `skills/home/gstack`
- local Docker gateway: `127.0.0.1:8181`
- gateway routes: `/mcp`, `/graph/*`, `/memory/status`, `/memory/query`, `/memory/curate`
- local Docker auth: none on loopback-only binds; hosted or tunnelled access must add auth

## Handoff Log

2026-04-12T13:25:00-06:00 - Official Kade-HQ memory base and launcher split aligned
Changed: promoted the official durable memory base to the `Kade-HQ` Obsidian vault, aligned repo mirrors to the `kade-hq` vault identity, and clarified that `kade-hq`, `g-kade`, and `gstack` all install as launcher surfaces while `g-kade` remains only the bridge skill.
Files: `AGENTS.md`, `.factory/memories.md`, `kade/AGENTS.md`, `kade/KADE.md`, installer tests, and the official Obsidian system map note.
Why: the repo contract still pointed at the old vault and still implied the launcher surface was only `g-kade` plus `gstack`, which no longer matched the intended system.
Verified: [x] grounded retrieval with `pk-qmd`; [x] repaired the installer/test regression; [ ] reran focused tests after the mirror update.
Next: keep the shell setup helpers in parity with the corrected PowerShell bootstrap and update any legacy Obsidian mirror note to point at the official `Kade-HQ` vault.

2026-04-11T18:41:02-06:00 - Intentional memory alignment
Changed: refreshed the durable memory contract to reflect the repo-owned `deps/pk-skills1` runtime, the loopback-only Docker gateway, and the local-vs-hosted security split.
Files: `AGENTS.md`, `.factory/memories.md`, `kade/AGENTS.md`, `kade/KADE.md`, Obsidian `llm_wiki_prompt_packet System Map.md`, and the vault log.
Why: repo and Obsidian memory were stale relative to the implemented bootstrap, Docker, and gateway behavior.
Verified: [x] inspected repo memory files; [x] attempted qmd retrieval for grounding; [x] aligned repo memory mirrors to the same contract.
Next: keep the top-level installer wrappers and hosted edge docs aligned with the same first-class gateway contract.

2026-04-11T19:18:00-06:00 - HUMAN profile seeding corrected
Changed: pointed the g-kade workspace installer at the packaged Kade-HQ Layer 1 profile, preserved real existing `~/.kade/HUMAN.md` files, and upgraded only the exact legacy stub.
Files: `installers/install_g_kade_workspace.py`, `tests/test_install_g_kade_workspace.py`, `AGENTS.md`, `.factory/memories.md`, `kade/KADE.md`, Obsidian `llm_wiki_prompt_packet System Map.md`, and `C:\Users\prest\.kade\HUMAN.md`.
Why: the installer was still generating the generic HUMAN stub instead of the Kade-HQ profile and needed an explicit preserve-existing rule.
Verified: [x] `python tests\test_install_g_kade_workspace.py`; [x] refreshed the live `~/.kade/HUMAN.md` only because it matched the exact legacy stub.
Next: keep future install and migration paths on the same rule: seed or upgrade the legacy stub, but preserve any real existing Layer 1 profile.
