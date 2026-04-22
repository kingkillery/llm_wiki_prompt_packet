# LLM Wiki Memory Packet

This repo is the prompt packet and vault installer for the `llm-wiki-memory` stack:

- `Kade-HQ` and `G-Stack` provide the agent harness layer
- `pk-qmd` is the source-evidence retrieval plane
- `Byterover` (`brv`) is the curated durable-memory plane
- `GitVizz` is the repo graph and web surface
- `llm-wiki-skills` is the local-first reusable skill lifecycle plane

The intended system combines `Kade-HQ`, `G-Stack`, `Byterover`, `GitVizz`, and `pk-qmd` into one contract, while still supporting local-first bootstrap paths.

The packet installs concise guidance files, tool-specific command/workflow files, a stack config, and health-check scripts into an Obsidian vault. It does not hide these components from maintainers, but the installed prompts tell agents to present one coherent intelligence surface to end users.

The installer can also seed packet-owned `kade-hq`, `gstack`, `g-kade`, and `llm-wiki-skills` wrapper skills into the user's home skill roots when you explicitly opt in with `--install-home-skills` or `LLM_WIKI_INSTALL_HOME_SKILLS=1`:

- `~/.agents/skills/`
- `~/.codex/skills/`
- `~/.claude/skills/`
- `~/.pi/agent/skills/`

Those wrappers live in this repo under `skills/home/` and are intentionally light. They are the packet-owned bridge layer, not a vendored copy of the full upstream `gstack` runtime bundle. The richer `gstack` and `g-kade` pieces are expected to arrive from the `deps/pk-skills1` submodule when that bootstrap path is enabled.

## Quick Install

**One command - wire this packet into the repo or vault you are sitting in.**

Windows (PowerShell):
```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1))) -WireRepo
```

macOS / Linux:
```bash
curl -fsSL https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.sh | bash -s -- --wire-repo
```

`-WireRepo` / `--wire-repo` runs preflight (detects missing tools), installs the packet into the current directory as a workspace, automates global Claude wiring (`~/.claude/CLAUDE.md` plus `~/.claude/commands/wiki-*.md`), and runs the health check as the closing step.

See [`QUICKSTART.md`](QUICKSTART.md) for the 30-second walkthrough, or run `bash install.sh --help` / `install.ps1 -Help` for the full flag set.

**Vault-only install** (legacy `packet` mode for an Obsidian vault, no global Claude wiring):
```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1)))
```
```bash
curl -fsSL https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.sh | bash
```

## Architecture

The stack contract baked into this packet is:

- use `pk-qmd` first for repo-specific evidence, docs, prompts, notes, and exact local behavior
- use `brv` for durable preferences, workflow quirks, and reused project decisions
- use `llm-wiki-skills` for reusable task shortcuts, feedback, and retirement
- treat `Kade-HQ` and `G-Stack` as part of the same system contract, not as an unrelated optional add-on
- prefer direct source evidence over memory when they conflict
- treat `GitVizz` as the local graph surface, with frontend and backend URLs configured explicitly
- do not expect end users to manage raw tool choices

## What the packet installs

### Shared root

- `AGENTS.md`
- `CLAUDE.md`
- `LLM_WIKI_MEMORY.md`
- `SKILL_CREATION_AT_EXPERT_LEVEL.md`

### Claude Code

- `.claude/commands/wiki-ingest.md`
- `.claude/commands/wiki-query.md`
- `.claude/commands/wiki-lint.md`
- `.claude/commands/wiki-skill.md`

### Codex

- `.agents/skills/llm-wiki-organizer/SKILL.md`
- `.agents/skills/llm-wiki-organizer/assets/system-prompt.md`
- `.agents/skills/llm-wiki-organizer/assets/tool-directives.md`
- `.agents/skills/llm-wiki-organizer/assets/output-contract.md`

### Antigravity

- `.agent/workflows/wiki-ingest.md`
- `.agent/workflows/wiki-query.md`
- `.agent/workflows/wiki-lint.md`
- `.agent/workflows/wiki-skill.md`

### Stack config and health checks

- `.llm-wiki/config.json`
- `.llm-wiki/package.json`
- `.llm-wiki/qmd-embed-state.json`
- `.llm-wiki/skills-registry.json`
- `.brv/context-tree/.gitkeep`
- `scripts/llm_wiki_packet.py`
- `scripts/llm_wiki_packet.ps1`
- `scripts/llm_wiki_packet.sh`
- `scripts/llm_wiki_packet.cmd`
- `scripts/check_llm_wiki_memory.ps1`
- `scripts/check_llm_wiki_memory.sh`
- `scripts/llm_wiki_skill_mcp.py`
- `scripts/llm_wiki_agent_failure_capture.py`
- `scripts/run_llm_wiki_agent.ps1`
- `scripts/run_llm_wiki_agent.sh`
- `scripts/run_llm_wiki_agent.cmd`
- `scripts/setup_llm_wiki_memory.ps1`
- `scripts/setup_llm_wiki_memory.sh`
- `scripts/qmd_embed_runner.mjs`
- `scripts/brv_query.ps1`
- `scripts/brv_query.sh`
- `scripts/brv_curate.ps1`
- `scripts/brv_curate.sh`
- `scripts/gitvizz_api.ps1`
- `scripts/gitvizz_api.sh`
- `scripts/launch_gitvizz.ps1`
- `scripts/launch_gitvizz.sh`

### Home skill roots

- `~/.agents/skills/kade-hq/SKILL.md`
- `~/.agents/skills/gstack/SKILL.md`
- `~/.agents/skills/g-kade/SKILL.md`
- `~/.agents/skills/llm-wiki-skills/SKILL.md`
- `~/.codex/skills/kade-hq/SKILL.md`
- `~/.codex/skills/gstack/SKILL.md`
- `~/.codex/skills/g-kade/SKILL.md`
- `~/.codex/skills/llm-wiki-skills/SKILL.md`
- `~/.claude/skills/kade-hq/SKILL.md`
- `~/.claude/skills/gstack/SKILL.md`
- `~/.claude/skills/g-kade/SKILL.md`
- `~/.claude/skills/llm-wiki-skills/SKILL.md`

### Bootstrapped vault directories

- `raw/`
- `raw/assets/`
- `wiki/`
- `wiki/index.md`
- `wiki/log.md`
- `wiki/sources/`
- `wiki/entities/`
- `wiki/concepts/`
- `wiki/syntheses/`
- `wiki/comparisons/`
- `wiki/timelines/`
- `wiki/questions/`
- `wiki/skills/index.md`
- `wiki/skills/active/`
- `wiki/skills/feedback/`
- `wiki/skills/retired/`
- `templates/`
- `scripts/`

## Bootstrap path

The packet configures the stack, but the easiest path is now the hosted installer. It prompts for the vault folder when you do not pass one, lays down the packet, and then runs the vault setup helper unless you explicitly skip it.

Local-first use remains supported. When you want a single hosted surface, the intended Docker mode should be able to host the qmd + gitvizz + brv stack together while keeping the same contract boundaries.

Use the installed helpers from the vault root when you want machine-level setup, repeatable verification, or a re-run after changing config:

- `scripts/setup_llm_wiki_memory.ps1`
- `scripts/setup_llm_wiki_memory.sh`
- `scripts/check_llm_wiki_memory.ps1`
- `scripts/check_llm_wiki_memory.sh`
- `scripts/qmd_embed_runner.mjs`
- `scripts/llm_wiki_skill_mcp.py`
- `scripts/run_llm_wiki_agent.ps1`
- `scripts/run_llm_wiki_agent.sh`
- `scripts/run_llm_wiki_agent.cmd`

## Quickstart

Use this when you already have this packet checked out and want a CLI-style packet toolset that can activate a specific repo for the full harness contract, including `kade-hq`, `g-kade`, `gstack`, Pi-facing home skills, and the Pokemon benchmark surface.

PowerShell:

```powershell
$packet = "C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet"
$project = "C:\path\to\target-project"

$env:BYTEROVER_API_KEY = "<optional-key>"
$env:GEMINI_API_KEY = "<optional-key>"

powershell -NoProfile -ExecutionPolicy Bypass -File "$packet\support\scripts\llm_wiki_packet.ps1" `
  init `
  --project-root $project `
  --targets "claude,antigravity,codex,droid,pi" `
  --install-scope local `
  --allow-global-tool-install `
  --force
```

That command:

- bootstraps the packet into the target project
- installs the repo-local packet CLI under `scripts/llm_wiki_packet.*`
- wires repo-local `kade-hq`, `g-kade`, `gstack`, and `pokemon-benchmark` skill surfaces
- installs packet-owned home wrappers into `~/.agents`, `~/.codex`, `~/.claude`, and `~/.pi/agent`
- runs the shared setup/check flow for project-local `pk-qmd` and `brv`
- skips GitVizz during activation by default so a project can activate before the graph layer is up

When a project is ready to validate GitVizz too, re-run activation with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$packet\support\scripts\llm_wiki_packet.ps1" `
  init `
  --project-root $project `
  --targets "claude,antigravity,codex,droid,pi" `
  --install-scope local `
  --allow-global-tool-install `
  --enable-gitvizz `
  --force
```

After activation, the preferred repo-local toolset surface is:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\llm_wiki_packet.ps1 check
```

Smoke benchmark from the activated repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\llm_wiki_packet.ps1 pokemon-benchmark smoke
```

Framework benchmark from the activated repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\llm_wiki_packet.ps1 pokemon-benchmark framework --agent codex
```

Compatibility note:

- `support/scripts/activate_llm_wiki_project.ps1` still exists, but it now forwards to `llm_wiki_packet.ps1 init`. Prefer the packet CLI surface for new automation and agent instructions.

If you want the direct health helper, this still works from the project root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_llm_wiki_memory.ps1
```

The setup helper now also wires a second local MCP server:

- server key: `llm-wiki-skills`
- command shape: `python scripts/llm_wiki_skill_mcp.py mcp --workspace <vault>`

That server exposes local-first skill lifecycle tools:

- `skill_lookup`
- `skill_reflect`
- `skill_validate`
- `skill_pipeline_run`
- `skill_propose`
- `skill_feedback`
- `skill_get`
- `skill_retire`

The pipeline now keeps internal skill-learning artifacts under:

- `.llm-wiki/skill-pipeline/briefs/`
- `.llm-wiki/skill-pipeline/deltas/`
- `.llm-wiki/skill-pipeline/validations/`
- `.llm-wiki/skill-pipeline/packets/`

Failure capture now has two surfaces:

- Claude Code: project-local `.claude/settings.local.json` hooks record `PostToolUseFailure` and `StopFailure` automatically.
- Claude Code, Codex, Factory Droid, and `pi`: the shared launcher wrapper `scripts/run_llm_wiki_agent.*` records non-zero CLI exits into the same failure collector, which is the intended path for Codex, Droid, and `pi`.

The intended loop is:

1. finish the task or trajectory
2. emit a reducer packet plus artifact refs for the important context
3. validate the candidate and route semantics for privacy, evidence quality, and duplicate overlap
4. merge into an existing skill or save a new one only when the route decision is `complete`

For long tasks, the reducer packet is mandatory. Think middle managers organizing the signal for executives, not a vague recap.

### 1. Install the custom `pk-qmd` fork

The canonical repo is:

- `https://github.com/kingkillery/pk-qmd`

The packet-local dependency manifest installs this fork first when you run the hosted bootstrap, so you only need the manual path when you want to work from a standalone checkout.

If you already have the fork locally, use that checkout instead of recloning.

Typical manual install from a checkout:

```powershell
npm install --prefix .\.llm-wiki
.\.llm-wiki\node_modules\.bin\pk-qmd.cmd --help
```

or install from the fork checkout directly:

```powershell
git clone https://github.com/kingkillery/pk-qmd.git pk-qmd
cd pk-qmd
bun install
bun link
pk-qmd --help
```

After `pk-qmd` is installed, run the vault setup helper to wire MCP config and bootstrap the collection:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_llm_wiki_memory.ps1
```

```bash
bash ./scripts/setup_llm_wiki_memory.sh
```

Key fork behavior this packet assumes:

- command name is `pk-qmd`
- shared MCP endpoint is `http://localhost:8181/mcp`
- the fork adds Gemini-backed multimodal commands such as `pk-qmd membed`, `pk-qmd msearch`, and `pk-qmd simage`

### 1b. Wire the harness layer

The packet-owned `gstack` and `g-kade` bridge skills are kept light on purpose. The fuller harness pieces are expected to be pulled in through repo-owned dependency or submodule paths during bootstrap, not assumed to already exist as a fully vendored runtime. When those paths are present, the setup flow should mount them into the home skill roots and preserve the local packet wrappers as the stable entry point.

### 2. Install and authenticate Byterover

Install `brv` using the official path for your platform:

- Apple Silicon macOS or Linux: `curl -fsSL https://byterover.dev/install.sh | sh`
- Windows or macOS Intel: `npm install -g byterover-cli`

Then authenticate with one of:

```bash
brv login --api-key <key>
```

or:

```bash
export BYTEROVER_API_KEY=<key>
```

The packet reserves `.brv/` and `.brv/context-tree/` inside the vault, but it does not author `.brv/config.json` for you.
In current BRV versions, `brv status` will initialize workspace-local BRV state automatically.

### 3. Run GitVizz with the correct local split

This packet assumes:

- frontend origin: `http://localhost:3000/`
- backend origin: `http://localhost:8003/`

For local GitHub App wiring, use:

- Homepage URL: `http://localhost:3000/`
- Setup URL: `http://localhost:3000/`
- Callback URL: `http://localhost:3000/api/auth/callback/github`

Do not treat `localhost:3000` as the backend API origin. The packet writes both frontend and backend URLs into `.llm-wiki/config.json`.

### Full-system helper

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_llm_wiki_memory.ps1 -QmdSource "C:\path\to\pk-qmd-main"
```

Shell:

```bash
bash ./scripts/setup_llm_wiki_memory.sh --qmd-source "/path/to/pk-qmd-main"
```

If you are launching a packet `.sh` helper from PowerShell, use the installed bridge so Git Bash receives translated paths:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\invoke_bash_helper.ps1 `
  -ScriptPath .\scripts\setup_llm_wiki_memory.sh `
  --verify-only
```

The hosted installers call this helper automatically unless `LLM_WIKI_SKIP_SETUP=1` is set. Use it directly when you want to re-run bootstrap or verification after the packet is already installed.

What the setup helper now does:

- installs or verifies `pk-qmd`
- prefers the packet-local dependency manifest at `.llm-wiki/package.json`
- falls back to `kingkillery/pk-qmd` only when packet-local install is unavailable and `LLM_WIKI_ALLOW_GLOBAL_TOOL_INSTALL=1` is set
- wires Claude/Codex/Factory MCP configs
- adds a QMD collection for the current vault
- adds default collection context
- runs `pk-qmd update`
- runs `pk-qmd embed`
- runs `pk-qmd membed` when `GEMINI_API_KEY` is set
- validates `brv status --format json`
- lets `brv status` initialize `.brv/config.json` and `.brv/context-tree` when missing
- launches GitVizz with `docker-compose up -d --build` when `gitvizz.repo_path` is configured and the endpoints are down

Health-check only:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_llm_wiki_memory.ps1
```

```bash
bash ./scripts/check_llm_wiki_memory.sh
```

## Installer usage

### Hosted one-command install

Run these from inside the target vault if you want the current directory used automatically. If you omit the vault path, the installers now prompt for it and then run the full setup helper.

Set `LLM_WIKI_SKIP_SETUP=1` if you only want the packet files and plan to run the helper later.
Home skill install is now opt-in: pass `--install-home-skills` or set `LLM_WIKI_INSTALL_HOME_SKILLS=1` if you want packet-owned wrappers in `~/.agents`, `~/.codex`, `~/.claude`, or `~/.pi/agent`.
Set `LLM_WIKI_ALLOW_GLOBAL_TOOL_INSTALL=1` if you want setup to fall back to global npm installs after packet-local install paths fail.

PowerShell:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1)))
```

`cmd.exe`:

```bat
%windir%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1)))"
```

Shell:

```bash
curl -fsSL https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.sh | bash
```

Override the vault path explicitly:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1))) -Vault "C:\path\to\Your Vault"
```

```bash
curl -fsSL https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.sh | bash -s -- "/path/to/Your Vault"
```

Override targets, branch or tag, and force mode:

```powershell
$env:LLM_WIKI_TARGETS = "claude,codex"
$env:LLM_WIKI_REF = "main"
$env:LLM_WIKI_FORCE = "1"
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1)))
```

```bash
curl -fsSL https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.sh | bash -s -- "$PWD" "claude,codex" --force main
```

### Stack URL overrides

The installer writes `.llm-wiki/config.json` using these defaults:

- `LLM_WIKI_QMD_COMMAND=pk-qmd`
- `LLM_WIKI_QMD_REPO_URL=https://github.com/kingkillery/pk-qmd`
- `LLM_WIKI_QMD_MCP_URL=http://localhost:8181/mcp`
- `LLM_WIKI_QMD_COLLECTION=<vault-folder-name>`
- `LLM_WIKI_QMD_CONTEXT=Primary llm-wiki-memory vault for <vault-path>`
- `LLM_WIKI_BRV_COMMAND=brv`
- `LLM_WIKI_GITVIZZ_FRONTEND_URL=http://localhost:3000`
- `LLM_WIKI_GITVIZZ_BACKEND_URL=http://localhost:8003`
- `LLM_WIKI_GITVIZZ_REPO_URL=<optional git URL for managed checkout>`
- `LLM_WIKI_GITVIZZ_CHECKOUT_PATH=<optional managed checkout path>`
- `LLM_WIKI_GITVIZZ_REPO_PATH=<optional local checkout path>`

### Docker container

The repo now includes a containerized bootstrap path for the packet-managed stack.

What it does:

- builds a Linux image with `node`, `npm`, `python3`, `git`, and `brv`
- installs the packet into a mounted vault at container start
- runs `scripts/setup_llm_wiki_memory.sh` inside the container
- persists container-local Claude/Codex/Factory MCP config under a named Docker volume
- starts `pk-qmd mcp` as the container foreground process by default

Quick start:

```bash
mkdir -p .docker/vault
docker compose up --build
```

Default container behavior:

- vault mount: `./.docker/vault -> /workspace`
- host gateway bind: `127.0.0.1:8181` by default
- `pk-qmd` is exposed on `/mcp`
- GitVizz backend is exposed on `/graph/*`
- BRV is exposed through `/memory/status`, `/memory/query`, and `/memory/curate`
- targets installed into the mounted vault: `claude,codex,droid,pi`
- GitVizz checks are skipped by default in-container unless you opt in
- optional full-stack mode can also wire in-container GitVizz services from a mounted GitVizz checkout
- local Docker mode does not require auth on these routes because the host bind is loopback-only

Useful overrides:

- `LLM_WIKI_MCP_BIND_HOST=127.0.0.1`
- `LLM_WIKI_VAULT_PATH=/absolute/path/to/vault`
- `LLM_WIKI_TARGETS=claude,codex,droid,pi`
- `LLM_WIKI_FORCE_INSTALL=1`
- `LLM_WIKI_QMD_SOURCE=/path/to/pk-qmd`
- `LLM_WIKI_ENABLE_GITVIZZ=1`
- `LLM_WIKI_GITVIZZ_SOURCE_HOST_PATH=/absolute/path/to/GitVizz`
- `LLM_WIKI_AGENT_API_TOKEN=<optional bearer token for hosted use>`
- `BYTEROVER_API_KEY=<key>`
- `GEMINI_API_KEY=<key>`
- `GH_TOKEN=<token>` or `GITHUB_TOKEN=<token>` for private `pk-qmd` fetches
- `LLM_WIKI_SKIP_GITVIZZ=0`
- `LLM_WIKI_MCP_SERVER_CMD="pk-qmd mcp"`

Host agent examples:

```bash
curl http://127.0.0.1:8181/healthz
curl http://127.0.0.1:8181/graph/openapi.json
curl -X POST http://127.0.0.1:8181/memory/query -H "Content-Type: application/json" -d '{"query":"what prior decisions matter here?"}'
```

If the `pk-qmd` repo is private in your environment and you already have a local checkout, use the local-checkout override so `serve` keeps that checkout mounted:

PowerShell:

```powershell
$env:LLM_WIKI_QMD_SOURCE_HOST_PATH = "C:\path\to\pk-qmd-main"
docker compose -f docker-compose.yml -f docker-compose.local-qmd.yml up --build
```

Shell:

```bash
export LLM_WIKI_QMD_SOURCE_HOST_PATH=/absolute/path/to/pk-qmd-main
docker compose -f docker-compose.yml -f docker-compose.local-qmd.yml up --build
```

If you want the packet container to talk to in-container GitVizz services instead of an external endpoint, enable the GitVizz profile and mount a real GitVizz checkout:

```bash
export COMPOSE_PROFILES=gitvizz
export LLM_WIKI_ENABLE_GITVIZZ=1
export LLM_WIKI_GITVIZZ_SOURCE_HOST_PATH=/absolute/path/to/GitVizz
export LLM_WIKI_QMD_SOURCE_HOST_PATH=/absolute/path/to/pk-qmd-main
docker compose -f docker-compose.yml -f docker-compose.local-qmd.yml up --build
```

If the `kingkillery/pk-qmd` repo is not anonymously installable in your environment, mount a local checkout and point the container at it:

```bash
docker compose run --rm \
  -e LLM_WIKI_QMD_SOURCE=/qmd-source \
  -v /absolute/path/to/pk-qmd:/qmd-source \
  llm-wiki bootstrap
```

If the repo is private but reachable with a GitHub token, export `GH_TOKEN` or `GITHUB_TOKEN` before `docker compose up` and the container entrypoint will configure git for authenticated fetches.

One-off commands:

```bash
docker compose run --rm llm-wiki init
docker compose run --rm llm-wiki bootstrap
docker compose run --rm llm-wiki health
docker compose run --rm llm-wiki shell
```

Notes:

- the container health check skips GitVizz unless you opt in with `LLM_WIKI_ENABLE_GITVIZZ=1` or `LLM_WIKI_SKIP_GITVIZZ=0`
- if you want GitVizz included in the health path, either point the stack URLs at a reachable GitVizz frontend/backend or enable the `gitvizz` compose profile with a mounted checkout
- the MCP config written by the setup helper lives inside the container home volume, not your host home directory

### Google Cloud VM

For hosted use, prefer a Google Compute Engine VM over Cloud Run for the current container shape.
This image writes packet state, MCP config, and vault data to a persistent writable filesystem, so a long-lived VM with Docker bind mounts is the simpler fit.

What the GCE deployment path does:

- builds the existing container with Cloud Build
- pushes the image to Artifact Registry
- creates or reuses a Compute Engine VM
- installs Docker and the Compose plugin on first boot
- runs the packet container with persistent bind mounts for `/workspace` and `/home/llmwiki`

Files added for this path:

- `deploy/gcp/compose.yaml`
- `deploy/gcp/compose.local-qmd.yml`
- `deploy/gcp/llm-wiki.env.example`
- `deploy/gcp/startup.sh`
- `deploy/gcp/deploy_compute_engine.sh`
- `deploy/gcp/deploy_compute_engine.ps1`

Quick start from Git Bash or WSL:

```bash
bash ./deploy/gcp/deploy_compute_engine.sh
```

Quick start from PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\gcp\deploy_compute_engine.ps1
```

Common overrides:

- `PROJECT_ID=<gcp-project-id>`
- `REGION=us-central1`
- `ZONE=us-central1-a`
- `INSTANCE_NAME=llm-wiki-packet`
- `MACHINE_TYPE=e2-standard-2`
- `OPEN_PUBLIC_MCP=1`
- `PUBLIC_MCP_SOURCE_RANGES=203.0.113.0/24`
- `LLM_WIKI_MCP_PORT=8181`
- `LLM_WIKI_TARGETS=claude,codex,droid,pi`
- `LLM_WIKI_SKIP_GITVIZZ=1`
- `LLM_WIKI_QMD_SOURCE=/absolute/path/to/local/pk-qmd-main`
- `LLM_WIKI_QMD_MCP_URL=https://mcp.example.com/mcp`
- `BYTEROVER_API_KEY=<key>`
- `GEMINI_API_KEY=<key>`
- `GH_TOKEN=<token>` or `GITHUB_TOKEN=<token>` for authenticated `pk-qmd` fetches

Notes:

- the deploy script grants the VM service account `roles/artifactregistry.reader`
- the deploy script does not open the MCP port publicly unless you set `OPEN_PUBLIC_MCP=1` or provide `PUBLIC_MCP_SOURCE_RANGES`
- if `LLM_WIKI_QMD_MCP_URL` is left blank, the packet config stays on `http://127.0.0.1:8181/mcp` inside the VM and expects an edge URL to be provided separately for remote clients
- if `LLM_WIKI_QMD_SOURCE` points at a local `pk-qmd` checkout, the deploy script uploads that checkout to the VM and mounts it into the container
- local Docker remains the fastest fallback path when you only need the service on one machine

### Cloudflare edge in front of GCP

For remote MCP or app clients, the clean hosted split is:

- use a `Worker` as the public API edge on a hostname like `mcp.example.com`
- point that Worker at a Cloudflare `Tunnel` hostname such as `mcp-origin.example.com`
- protect the tunnel hostname with `Access` and let the Worker send an Access service token to the origin
- keep GitVizz on its own hostname, usually `gitvizz.example.com`, behind interactive Access instead of routing it through the packet Worker

The repo includes a minimal scaffold for this path:

- `deploy/cloudflare/README.md`
- `deploy/cloudflare/mcp-edge-worker.js`
- `deploy/cloudflare/wrangler.jsonc.example`

Operational notes:

- the packet VM in this repo only hosts the MCP-facing packet service by default
- GitVizz can still stay a separate runtime with its own compose stack, but this repo also supports an opt-in containerized local GitVizz path when you mount a checkout and enable the compose profile
- `brv` remains a private memory plane; expose curated app-level routes, not raw BRV provider credentials or direct provider calls

### GitVizz command-line wrapper

The packet now installs thin wrappers for GitVizz backend access and local launch.

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gitvizz_api.ps1 -Path /api/backend-chat/health
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gitvizz_api.ps1 -UseApiBase -Path /backend-chat/models/available
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\launch_gitvizz.ps1 -Rebuild
```

Shell:

```bash
bash ./scripts/gitvizz_api.sh --path /api/backend-chat/health
```

```bash
bash ./scripts/gitvizz_api.sh --use-api-base --path /backend-chat/models/available
```

```bash
bash ./scripts/launch_gitvizz.sh --rebuild
```

### BRV command-line wrappers

Use the installed wrappers when you want stable BRV access from the vault workspace.

Important:

- `brv status` is local-first and works without provider connection.
- `brv query` and `brv curate` require a connected provider.
- Quick start: `brv providers connect byterover`

Current packet default:

- provider: `openrouter`
- model: `google/gemini-3.1-flash-lite-preview`

Explicit BRV provider split:

- default query path: `openrouter` + `google/gemini-3.1-flash-lite-preview`
- default curate path: `openrouter` + `google/gemini-3.1-flash-lite-preview`
- native `google` + `google/gemini-3.1-flash-lite-preview` is kept as a query-only experiment path

Current BRV model options retained in the packet:

- `google/gemini-3.1-flash-lite-preview`
- `openai/gpt-oss-safeguard-20b`
- `x-ai/grok-4.20-multi-agent`
- `liquid/lfm-2.5-1.2b-thinking:free`
- `openai/gpt-5-nano`
- `arcee-ai/trinity-large-thinking`

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_query.ps1 -Query "what prior decisions matter here?"
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_curate.ps1 -Content "Persist only durable workflow facts"
```

Shell:

```bash
bash ./scripts/brv_query.sh --query "what prior decisions matter here?"
```

Native Google query experiment:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_query.ps1 -UseQueryExperiment -Query "what prior decisions matter here?"
```

```bash
bash ./scripts/brv_query.sh --use-query-experiment --query "what prior decisions matter here?"
```

Explicit provider override:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_query.ps1 -Provider google -Model google/gemini-3.1-flash-lite-preview -Query "what prior decisions matter here?"
```

```bash
bash ./scripts/brv_query.sh --provider google --model google/gemini-3.1-flash-lite-preview --query "what prior decisions matter here?"
```

```bash
bash ./scripts/brv_curate.sh --content "Persist only durable workflow facts"
```

### BRV benchmark runner

The packet now includes a small BRV benchmark utility so you can rerun query-versus-curate provider tests on demand.

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_benchmark.ps1
```

Shell:

```bash
bash ./scripts/brv_benchmark.sh
```

Custom targets use `provider=model`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\brv_benchmark.ps1 `
  -Target openrouter=google/gemini-3.1-flash-lite-preview `
  -Target google=google/gemini-3.1-flash-lite-preview
```

Example:

```powershell
$env:LLM_WIKI_GITVIZZ_FRONTEND_URL = "http://localhost:3000"
$env:LLM_WIKI_GITVIZZ_BACKEND_URL = "http://localhost:8003"
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1)))
```

### Versioned public bootstrap path

Release assets are generated automatically by GitHub Actions from the checked-in root installers when a release is published. The release installers default to the release tag instead of `main`, and they behave like the hosted installer above: prompt for the vault folder, then run the full setup helper.

PowerShell:

```powershell
$tmp = Join-Path $env:TEMP 'llm-wiki-install.ps1'
Invoke-WebRequest https://github.com/kingkillery/llm_wiki_prompt_packet/releases/latest/download/install.ps1 -OutFile $tmp
& $tmp
Remove-Item $tmp -Force
```

Shell:

```bash
curl -fsSL https://github.com/kingkillery/llm_wiki_prompt_packet/releases/latest/download/install.sh | bash
```

### Local installer

Use this when you only want to lay down the packet files. The hosted `install.sh` / `install.ps1` wrappers are the ones that prompt for the vault and then run the full bootstrap helper.

```bash
python3 installers/install_obsidian_agent_memory.py --vault "/path/to/Your Vault"
```

Optional flags:

```bash
python3 installers/install_obsidian_agent_memory.py \
  --vault "/path/to/Your Vault" \
  --targets claude,antigravity,codex,droid,pi \
  --force
```

### Cross-agent failure wrapper

Use the shared wrapper when you want the packet to capture CLI-level failures for any supported agent:

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_llm_wiki_agent.ps1 -Agent codex -Arguments exec,"analyze this repo"
```

Shell:

```bash
bash ./scripts/run_llm_wiki_agent.sh --agent droid -- exec "analyze this repo"
```

```bash
bash ./scripts/run_llm_wiki_agent.sh --agent pi -- -p "review the current diff"
```

```bash
bash ./scripts/run_llm_wiki_agent.sh --agent claude -- --print "summarize the changes"
```

In PowerShell, pass forwarded agent arguments through `-Arguments ...`; bare `--` is shell syntax for bash and `cmd`, not PowerShell.

This wrapper keeps Claude's native hook integration intact and adds process-level failure capture for Codex, Factory Droid, and `pi`, which do not expose a matching failure-event hook surface in the packet today.

Install into a test home directory instead of your real user profile:

```bash
python3 installers/install_obsidian_agent_memory.py \
  --vault "/path/to/Your Vault" \
  --home-root "/tmp/llm-wiki-home"
```

Dry run:

```bash
python3 installers/install_obsidian_agent_memory.py --vault "/path/to/Your Vault" --dry-run
```

## Verification

After the packet is installed and the tools are present, run:

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_llm_wiki_memory.ps1
```

Shell:

```bash
bash ./scripts/check_llm_wiki_memory.sh
```

These checks verify:

- the stack config exists
- the packet-local QMD dependency manifest exists
- `pk-qmd` is on PATH and responds to `status`
- the expected vault QMD collection exists when the richer fork is installed
- `brv` is on PATH
- `.brv/config.json` exists in the vault
- the configured GitVizz frontend and backend ports are reachable

## Assumptions

- the Obsidian vault is also the working directory for your agents
- `pk-qmd` is the canonical retrieval command name
- BRV is durable memory, not the primary evidence source
- GitVizz is reachable locally unless you override the URLs
