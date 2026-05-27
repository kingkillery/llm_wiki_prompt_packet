# LLM Wiki Memory Stack

> **Audience:** Agents operating inside an installed llm-wiki vault. For repo-level architecture and the canonical-layer contract, see [`SYSTEM_CONTRACT.md`](SYSTEM_CONTRACT.md).

This vault expects the following tooling stack around the markdown wiki:

- `Kade-HQ` and `G-Stack` for the agent harness and local bootstrap surface
- `pk-qmd` for repo-local evidence retrieval and MCP-backed search
- `GitVizz` for local repo graph and web access

## Routing rules

Treat the stack as a routing system:

- Use `pk-qmd` first for exact evidence retrieval, prompt/docs lookup, and difficult broad searches when you do not yet know the right repo area.
- Use `GitVizz` first for repository topology, API surface, route relationships, dependency navigation, and for honing in after `pk-qmd` has located the likely folder or subsystem.
- Treat `gstack` and `g-kade` as surfaces supplied by the `deps/pk-skills1` submodule when the bootstrap path is enabled; do not describe them as fully vendored runtime bundles unless the checkout actually contains them.

Typical flow:

1. `pk-qmd` finds the likely file, folder, prompt, or note.
2. `GitVizz` maps the surrounding repo structure or API shape.

The canonical stack settings live in `.llm-wiki/config.json`.
The local dependency manifest for packet-managed installs lives in `.llm-wiki/package.json`.
The current repo may only ship thin wrappers for some harness pieces; bootstrap is responsible for surfacing the expected dependency or submodule paths when present.

## Modern memory layering

Adopt a modular memory stack instead of treating all memory as one bucket:

- **Working memory**: active prompt context, `AGENTS.md`, `CLAUDE.md`, and currently open files.
- **Episodic memory**: task briefs, reducer packets, and failure/evolution artifacts under `.llm-wiki/skill-pipeline/`.
- **Semantic memory**: durable repo knowledge in `wiki/` pages such as concepts, syntheses, comparisons, and timelines.
- **Procedural memory**: reusable skills under `wiki/skills/active/` plus their feedback and retirement history.

Preferred promotion flow:

1. a task produces raw evidence
2. a reducer packet captures the episode
3. durable facts are promoted into wiki pages or skills only after validation
4. stale or conflicting procedural memory is amended, merged, or retired instead of silently accumulating

Controller rule of thumb:

- decide explicitly whether the current turn needs a **READ**, **WRITE**, **UPDATE**, or no memory operation
- prefer lean state plus targeted retrieval over replaying large history
- reuse stable summaries when possible instead of re-reading the same long context
- use `llm-wiki-packet context --task "..."` for the default compact context bundle
- use `llm-wiki-packet evidence --query "..."`, `llm-wiki-packet evidence --plane source --query "..."`, or `llm-wiki-packet context --mode deep` when broad hybrid/source-backed retrieval is specifically useful
- Treat Hugging Face embedding/reranking settings in `.llm-wiki/config.json` as optional planner hints only; they are disabled by default and must not become a required bootstrap dependency.

Treat active skills as typed memory objects, not just markdown blobs. Each skill should carry:

- a primary memory scope (`procedural`, `episodic`, `semantic`, `working`, or `hybrid`)
- a memory strategy (`hierarchical` or `knowledge_object` by default; `flat` only for legacy/simple cases)
- durable facts worth preserving
- provenance refs for audit and deprecation
- an update strategy such as merge, replace-on-validation, or deprecate-on-conflict
- canonical reconciliation keys so write-time merge/update decisions are explicit instead of purely append-only

## Skill creation at expert level

This vault can also act as a reusable skill library.

Use the wiki to store operational shortcuts that future agents can exploit instead of rediscovering:

- `wiki/skills/index.md`
- `wiki/skills/active/`
- `wiki/skills/feedback/`
- `wiki/skills/retired/`

Internal pipeline artifacts live under:

- `.llm-wiki/skill-pipeline/briefs/`
- `.llm-wiki/skill-pipeline/deltas/`
- `.llm-wiki/skill-pipeline/validations/`
- `.llm-wiki/skill-pipeline/packets/`

When creating or updating a skill:

- emit a strong reducer packet plus artifact refs when the task had meaningful exploration cost
- capture the repeated trigger
- write the shortest reliable fast path
- include preconditions and failure modes
- record a reasoned review trail
- run a privacy gate before saving
- validate the candidate before promoting it to the active library
- merge deltas into an existing skill when overlap is high instead of creating a duplicate

Prefer the pipeline tools when the local MCP server is installed:

- `skill_lookup`
- `skill_reflect`
- `skill_validate`
- `skill_pipeline_run`
- `skill_propose`
- `skill_feedback`
- `skill_get`
- `skill_retire`

The implementation guide for this lives in `SKILL_CREATION_AT_EXPERT_LEVEL.md`.

For long tasks, the parent path should consume the reducer packet by default and only pull raw detail from referenced artifacts when escalation is necessary.

### Harness lifecycle commands

Use the packet CLI to keep long-running agent work replayable and auditable:

- `llm-wiki-packet manifest --task "..."` creates a run id, success criteria, prompt/tool/model versions, and expected artifact paths.
- `llm-wiki-packet reduce --run-id <id> --source-file <path>` converts raw run output into claims, evidence, contradictions, durable facts, open questions, and skill candidates.
- `llm-wiki-packet evaluate --run-id <id>` scores the run for task success, citation quality, retrieval sufficiency, retrieval-plane health, and promotion readiness.
- `llm-wiki-packet promote --run-id <id>` records a memory-routing decision; add `--apply` only when the promotion is intentionally approved.
- `llm-wiki-packet improve --run-id <id>` creates a gated improvement proposal; it is accepted only when benchmark and no-regression gates pass.
- Add `--run-id <id>` to `context` or `evidence` when retrieval metadata should be written directly into the run manifest.

### Skill-index maintenance

- The packet automatically builds or refreshes `.llm-wiki/skill-index.json` during setup and health-check runs.
- Interactive wrapped agent launches and the read-only dashboard also lazily refresh the index when the active-skill set, retired-skill set, feedback log, or `.llm-wiki/config.json` changed.
- Do not ask end users to manually run index maintenance unless you are debugging the maintenance path itself. Manual fallback remains `python scripts/build_skill_index.py --workspace <repo>`.

## Defaults

- QMD command: `pk-qmd`
- GitVizz frontend: `http://localhost:3000`
- GitVizz backend: `http://localhost:8003`
- QMD MCP endpoint: `http://localhost:8181/mcp`

Local-first remains the default, but an optional Docker-hosted mode should be able to run the qmd + gitvizz stack together when a single hosted surface is preferred.

## `pk-qmd`

Use the packet-local dependency manifest first, or the custom `kingkillery/pk-qmd` fork.

Recommended install from the packet-managed manifest:

```powershell
npm install --prefix.\.llm-wiki
.\.llm-wiki\node_modules\.bin\pk-qmd.cmd --help
```

Fallback install from a checkout:

```powershell
git clone https://github.com/kingkillery/pk-qmd.git pk-qmd
cd pk-qmd
bun install
bun link
pk-qmd --help
```

After install, wire the MCP config from the fork repo if available:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\install-pk-qmd-mcp-all.ps1
```

## GitVizz

GitVizz is expected to run locally as:

- frontend: `http://localhost:3000/`
- backend: `http://localhost:8003/`

If you are configuring the GitHub App locally, keep these aligned:

- Homepage URL: `http://localhost:3000/`
- Setup URL: `http://localhost:3000/`
- Callback URL: `http://localhost:3000/api/auth/callback/github`

When you run the local Docker path, the host-facing gateway is loopback-only by default on `127.0.0.1:8181` and exposes:

- `/mcp` for `pk-qmd`
- `/graph/*` for the configured GitVizz backend

Local Docker mode does not require auth on those routes because the host bind is loopback-only. Set `LLM_WIKI_AGENT_API_TOKEN` only when you intentionally need a bearer gate, such as hosted or tunnelled access.

## Setup helpers

These vault-local helpers are installed with the packet:

- `scripts/setup_llm_wiki_memory.ps1`
- `scripts/setup_llm_wiki_memory.sh`
- `scripts/check_llm_wiki_memory.ps1`
- `scripts/check_llm_wiki_memory.sh`
- `scripts/qmd_embed_runner.mjs`
- `scripts/llm_wiki_skill_mcp.py`
- `scripts/invoke_bash_helper.ps1`
- `scripts/gitvizz_api.ps1`
- `scripts/gitvizz_api.sh`
- `scripts/launch_gitvizz.ps1`
- `scripts/launch_gitvizz.sh`
- `scripts/llm_wiki_skills.py`
- `scripts/llm_wiki_skills.ps1`
- `scripts/llm_wiki_skills.cmd`

Use the setup helper to:

- install missing CLIs
- wire MCP configs
- bootstrap a QMD collection for the current vault
- add default collection context
- run `pk-qmd update`
- run `pk-qmd embed`
- run `pk-qmd membed` when `GEMINI_API_KEY` is present
- wire the local skill MCP server
- auto-launch or acquire GitVizz when `gitvizz.repo_url`, `gitvizz.checkout_path`, or `gitvizz.repo_path` are configured
- verify the local GitVizz endpoints

### GitVizz command-line access

Use the installed GitVizz API helper when you want command-line access to the backend:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\gitvizz_api.ps1 -Path /api/backend-chat/health
```

```bash
bash./scripts/gitvizz_api.sh --path /api/backend-chat/health
```

If you want `/api` prepended automatically, use the API-base mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\gitvizz_api.ps1 -UseApiBase -Path /backend-chat/models/available
```

```bash
bash./scripts/gitvizz_api.sh --use-api-base --path /backend-chat/models/available
```

When a local GitVizz checkout is configured, use the launcher helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\launch_gitvizz.ps1 -Rebuild
```

```bash
bash./scripts/launch_gitvizz.sh --rebuild
```

Managed GitVizz acquisition config lives alongside the endpoint URLs:

- `gitvizz.repo_url`
- `gitvizz.checkout_path`
- `gitvizz.repo_path`
- `gitvizz.repo_id`
- `gitvizz.authorization_env`
- `gitvizz.auth_token_env`

Environment overrides:

- `LLM_WIKI_GITVIZZ_REPO_URL`
- `LLM_WIKI_GITVIZZ_CHECKOUT_PATH`
- `LLM_WIKI_GITVIZZ_REPO_PATH`
- `LLM_WIKI_GITVIZZ_AUTHORIZATION`
- `LLM_WIKI_GITVIZZ_TOKEN`

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\setup_llm_wiki_memory.ps1
```

Shell:

```bash
bash./scripts/setup_llm_wiki_memory.sh
```

If you are in PowerShell and need to invoke a packet `.sh` helper directly, use the Bash bridge so Windows paths are translated correctly for Git Bash:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\invoke_bash_helper.ps1 `
 -ScriptPath.\scripts\setup_llm_wiki_memory.sh `
 --verify-only
```

When your current `pk-qmd` on PATH is the stripped-down build without `collection` and `context` commands, point the helper at the richer local checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\setup_llm_wiki_memory.ps1 -QmdSource "C:\path\to\pk-qmd-main"
```

```bash
bash./scripts/setup_llm_wiki_memory.sh --qmd-source "/path/to/pk-qmd-main"
```

Use the health helper when you only want verification:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\check_llm_wiki_memory.ps1
```

```bash
bash./scripts/check_llm_wiki_memory.sh
```

PowerShell bridge example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File.\scripts\invoke_bash_helper.ps1 `
 -ScriptPath.\scripts\check_llm_wiki_memory.sh
```

## Environment overrides

The setup helpers honor these environment variables:

- `LLM_WIKI_QMD_SOURCE`
- `LLM_WIKI_QMD_REPO_URL`
- `LLM_WIKI_QMD_COMMAND`
- `LLM_WIKI_QMD_COLLECTION`
- `LLM_WIKI_QMD_CONTEXT`
- `LLM_WIKI_GITVIZZ_FRONTEND_URL`
- `LLM_WIKI_GITVIZZ_BACKEND_URL`
- `LLM_WIKI_GITVIZZ_REPO_URL`
- `LLM_WIKI_GITVIZZ_CHECKOUT_PATH`
- `LLM_WIKI_GITVIZZ_REPO_PATH`
