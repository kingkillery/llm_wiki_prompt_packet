# LLM Wiki Memory Stack

This vault expects the following tooling stack around the markdown wiki:

- `Kade-HQ` and `G-Stack` for the agent harness and local bootstrap surface
- `pk-qmd` for repo-local evidence retrieval and MCP-backed search
- `brv` for durable memory capture and recall
- `GitVizz` for local repo graph and web access

## Routing rules

Treat the stack as a routing system:

- Use `pk-qmd` first for exact evidence retrieval, prompt/docs lookup, and difficult broad searches when you do not yet know the right repo area.
- Use `GitVizz` first for repository topology, API surface, route relationships, dependency navigation, and for honing in after `pk-qmd` has located the likely folder or subsystem.
- Use `brv` only for durable memory such as stable preferences, prior decisions, and repeated workflow quirks.
- Treat `gstack` and `g-kade` as surfaces supplied by the `deps/pk-skills1` submodule when the bootstrap path is enabled; do not describe them as fully vendored runtime bundles unless the checkout actually contains them.

Typical flow:

1. `pk-qmd` finds the likely file, folder, prompt, or note.
2. `GitVizz` maps the surrounding repo structure or API shape.
3. `brv` is consulted only if durable memory would materially improve the answer.

The canonical stack settings live in `.llm-wiki/config.json`.
The local dependency manifest for packet-managed installs lives in `.llm-wiki/package.json`.
The current repo may only ship thin wrappers for some harness pieces; bootstrap is responsible for surfacing the expected dependency or submodule paths when present.

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

## Defaults

- QMD command: `pk-qmd`
- BRV command: `brv`
- GitVizz frontend: `http://localhost:3000`
- GitVizz backend: `http://localhost:8003`
- QMD MCP endpoint: `http://localhost:8181/mcp`

Local-first remains the default, but an optional Docker-hosted mode should be able to run the qmd + gitvizz + brv stack together when a single hosted surface is preferred.

## `pk-qmd`

Use the packet-local dependency manifest first, or the custom `kingkillery/pk-qmd` fork.

Recommended install from the packet-managed manifest:

```powershell
npm install --prefix .\.llm-wiki
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
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-pk-qmd-mcp-all.ps1
```

## BRV

Install BRV with the official path for your platform:

- Apple Silicon macOS or Linux: `curl -fsSL https://byterover.dev/install.sh | sh`
- Windows or macOS Intel: `npm install -g byterover-cli`

Then authenticate with `brv login --api-key <key>` or `BYTEROVER_API_KEY`.

Important:

- `brv status` works before provider connection.
- `brv query` and `brv curate` require a connected provider.
- For the free built-in path, run `brv providers connect byterover`.
- For BYOK usage, connect a provider such as OpenAI, Anthropic, OpenRouter, or another supported backend.

Current preferred BRV provider and model:

- provider: `openrouter`
- default model: `google/gemini-3.1-flash-lite-preview`

Provider split:

- default query path: `openrouter` + `google/gemini-3.1-flash-lite-preview`
- default curate path: `openrouter` + `google/gemini-3.1-flash-lite-preview`
- query-only experiment path: native `google` + `google/gemini-3.1-flash-lite-preview`
- native Google is not the default curate path

Candidate BRV models currently kept as options:

- `google/gemini-3.1-flash-lite-preview`
- `openai/gpt-oss-safeguard-20b`
- `x-ai/grok-4.20-multi-agent`
- `liquid/lfm-2.5-1.2b-thinking:free`
- `openai/gpt-5-nano`
- `arcee-ai/trinity-large-thinking`

### BRV command-line access

Use the installed BRV wrappers for stable memory operations from the vault root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_query.ps1 -Query "what project decisions matter here?"
```

```bash
bash ./scripts/brv_query.sh --query "what project decisions matter here?"
```

Native Google query experiment:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_query.ps1 -UseQueryExperiment -Query "what project decisions matter here?"
```

```bash
bash ./scripts/brv_query.sh --use-query-experiment --query "what project decisions matter here?"
```

Explicit provider override:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_query.ps1 -Provider google -Model google/gemini-3.1-flash-lite-preview -Query "what project decisions matter here?"
```

```bash
bash ./scripts/brv_query.sh --provider google --model google/gemini-3.1-flash-lite-preview --query "what project decisions matter here?"
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_curate.ps1 -Content "Store only durable, reusable decisions here"
```

```bash
bash ./scripts/brv_curate.sh --content "Store only durable, reusable decisions here"
```

These wrappers:

- read the configured `brv` command from `.llm-wiki/config.json`
- run in the vault workspace so `.brv/` state stays local
- default to JSON-friendly output for automation
- default to the configured BRV provider and model unless overridden
- expect a connected BRV provider for `query` and `curate`

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
- `/memory/status`, `/memory/query`, and `/memory/curate` as a narrow BRV adapter

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
- `scripts/brv_query.ps1`
- `scripts/brv_query.sh`
- `scripts/brv_curate.ps1`
- `scripts/brv_curate.sh`
- `scripts/brv_benchmark.py`
- `scripts/brv_benchmark.ps1`
- `scripts/brv_benchmark.sh`
- `scripts/gitvizz_api.ps1`
- `scripts/gitvizz_api.sh`
- `scripts/launch_gitvizz.ps1`
- `scripts/launch_gitvizz.sh`

Use the setup helper to:

- install missing CLIs
- wire MCP configs
- bootstrap a QMD collection for the current vault
- add default collection context
- run `pk-qmd update`
- run `pk-qmd embed`
- run `pk-qmd membed` when `GEMINI_API_KEY` is present
- wire the local skill MCP server
- validate `brv status --format json`
- let `brv status` initialize `.brv/config.json` and `.brv/context-tree` when needed
- auto-launch or acquire GitVizz when `gitvizz.repo_url`, `gitvizz.checkout_path`, or `gitvizz.repo_path` are configured
- verify the local GitVizz endpoints

### BRV benchmark runner

Use the benchmark runner to compare query and curate behavior across provider/model pairs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_benchmark.ps1
```

```bash
bash ./scripts/brv_benchmark.sh
```

Override targets with `provider=model` pairs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_benchmark.ps1 `
  -Target openrouter=google/gemini-3.1-flash-lite-preview `
  -Target google=google/gemini-3.1-flash-lite-preview
```

```bash
bash ./scripts/brv_benchmark.sh \
  --target openrouter=google/gemini-3.1-flash-lite-preview \
  --target google=google/gemini-3.1-flash-lite-preview
```

### GitVizz command-line access

Use the installed GitVizz API helper when you want command-line access to the backend:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gitvizz_api.ps1 -Path /api/backend-chat/health
```

```bash
bash ./scripts/gitvizz_api.sh --path /api/backend-chat/health
```

If you want `/api` prepended automatically, use the API-base mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gitvizz_api.ps1 -UseApiBase -Path /backend-chat/models/available
```

```bash
bash ./scripts/gitvizz_api.sh --use-api-base --path /backend-chat/models/available
```

When a local GitVizz checkout is configured, use the launcher helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch_gitvizz.ps1 -Rebuild
```

```bash
bash ./scripts/launch_gitvizz.sh --rebuild
```

Managed GitVizz acquisition config lives alongside the endpoint URLs:

- `gitvizz.repo_url`
- `gitvizz.checkout_path`
- `gitvizz.repo_path`

Environment overrides:

- `LLM_WIKI_GITVIZZ_REPO_URL`
- `LLM_WIKI_GITVIZZ_CHECKOUT_PATH`
- `LLM_WIKI_GITVIZZ_REPO_PATH`

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_llm_wiki_memory.ps1
```

Shell:

```bash
bash ./scripts/setup_llm_wiki_memory.sh
```

If you are in PowerShell and need to invoke a packet `.sh` helper directly, use the Bash bridge so Windows paths are translated correctly for Git Bash:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\invoke_bash_helper.ps1 `
  -ScriptPath .\scripts\setup_llm_wiki_memory.sh `
  --verify-only
```

When your current `pk-qmd` on PATH is the stripped-down build without `collection` and `context` commands, point the helper at the richer local checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_llm_wiki_memory.ps1 -QmdSource "C:\path\to\pk-qmd-main"
```

```bash
bash ./scripts/setup_llm_wiki_memory.sh --qmd-source "/path/to/pk-qmd-main"
```

Use the health helper when you only want verification:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_llm_wiki_memory.ps1
```

```bash
bash ./scripts/check_llm_wiki_memory.sh
```

PowerShell bridge example:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\invoke_bash_helper.ps1 `
  -ScriptPath .\scripts\check_llm_wiki_memory.sh
```

## Environment overrides

The setup helpers honor these environment variables:

- `LLM_WIKI_QMD_SOURCE`
- `LLM_WIKI_QMD_REPO_URL`
- `LLM_WIKI_QMD_COMMAND`
- `LLM_WIKI_QMD_COLLECTION`
- `LLM_WIKI_QMD_CONTEXT`
- `LLM_WIKI_BRV_COMMAND`
- `LLM_WIKI_GITVIZZ_FRONTEND_URL`
- `LLM_WIKI_GITVIZZ_BACKEND_URL`
- `LLM_WIKI_GITVIZZ_REPO_URL`
- `LLM_WIKI_GITVIZZ_CHECKOUT_PATH`
- `LLM_WIKI_GITVIZZ_REPO_PATH`
