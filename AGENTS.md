You are working in `llm_wiki_prompt_packet`, the repo that develops and packages the combined `Kade-HQ` + `G-Stack` + `pk-qmd` + `Byterover` + `GitVizz` system.

Instruction priority:

1. System
2. Developer
3. Repo-local instructions and adjacent docs
4. User task
5. Default behavior

Operating mode:

- Be execution-first.
- Read before editing.
- Keep local and hosted responsibilities clearly separated.
- Treat memory maintenance as implementation work, not commentary.
- Make targeted edits only; do not rewrite unrelated sections.
- Do not revert unrelated changes you did not make.

Durable system contract:

- `Kade-HQ` and `G-Stack` are the harness layer.
- The richer repo-owned harness runtime lives under `deps/pk-skills1`.
- Packet-owned launcher wrappers live under `skills/home/g-kade` and `skills/home/gstack`, and optional home skill installs remain the launcher surface.
- `pk-qmd` is the source-grounded retrieval and embeddings plane.
- `Byterover` (`brv`) is the durable memory plane.
- `GitVizz` is the graph and web surface.
- Local Docker exposes a single loopback gateway on `127.0.0.1:8181`:
  - `/mcp` -> `pk-qmd`
  - `/graph/*` -> GitVizz backend
  - `/memory/*` -> narrow BRV adapter
- Local Docker intentionally does not require auth on that gateway because it binds to loopback only.
- Hosted or tunnelled access should add an auth layer and must not expose raw BRV credentials or internal GitVizz services.

Intentional memory loop:

1. Read this file, `.factory/memories.md`, and `kade/AGENTS.md` plus `kade/KADE.md` when present.
2. Use `qmd` first when you need repo-derived memory or history; use GitVizz when topology or route relationships matter.
3. Treat Obsidian as the durable source of truth for intentional memory:
   - `C:\dev\Desktop-Projects\Helpful-Docs-Prompts\VAULTS-OBSIDIAN\designandbuilding-vault\designandbuilding-vault\Guides and Docs\llm_wiki_prompt_packet System Map.md`
4. Mirror durable decisions back into repo memory files so the same intent is not represented differently across layers.
5. Keep launcher-wrapper expectations, repo-owned runtime expectations, and local-vs-hosted security expectations consistent.

Working rules:

- Prefer the underlying installers and setup helpers over stale wrapper assumptions.
- Treat thin wrappers as launcher surfaces, not proof that the richer runtime is installed.
- `g-kade` mode should keep installing the launcher into home skill roots by default because it is the entry surface.
- `installers/install_g_kade_workspace.py` should seed `~/.kade/HUMAN.md` from the packaged `kade-headquarters` profile only when the file is missing or still the exact legacy stub; do not overwrite a real existing Layer 1 profile.
- Keep the project-local `kade/` overlay aligned with the packet contract instead of replacing it.

Definition of done:

- Obsidian intentional memory is updated when durable intent changes.
- Repo memory mirrors are aligned with that update.
- `qmd` or GitVizz was used when retrieval or history grounding was needed.
- No unrelated files were changed.
