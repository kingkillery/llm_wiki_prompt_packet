# LLM Wiki Memory Packet

This repo is the prompt packet and vault installer for the `llm-wiki-memory` stack:

- `pk-qmd` is the source-evidence retrieval plane
- `Byterover` (`brv`) is the curated durable-memory plane
- `GitVizz` is the repo graph and web surface

The packet installs concise guidance files, tool-specific command/workflow files, a stack config, and health-check scripts into an Obsidian vault. It does not hide these components from maintainers, but the installed prompts tell agents to present one coherent intelligence surface to end users.

## Architecture

The stack contract baked into this packet is:

- use `pk-qmd` first for repo-specific evidence, docs, prompts, notes, and exact local behavior
- use `brv` for durable preferences, workflow quirks, and reused project decisions
- prefer direct source evidence over memory when they conflict
- treat `GitVizz` as the local graph surface, with frontend and backend URLs configured explicitly
- do not expect end users to manage raw tool choices

## What the packet installs

### Shared root

- `AGENTS.md`
- `CLAUDE.md`
- `LLM_WIKI_MEMORY.md`

### Claude Code

- `.claude/commands/wiki-ingest.md`
- `.claude/commands/wiki-query.md`
- `.claude/commands/wiki-lint.md`

### Codex

- `.agents/skills/llm-wiki-organizer/SKILL.md`
- `.agents/skills/llm-wiki-organizer/assets/system-prompt.md`
- `.agents/skills/llm-wiki-organizer/assets/tool-directives.md`
- `.agents/skills/llm-wiki-organizer/assets/output-contract.md`

### Antigravity

- `.agent/workflows/wiki-ingest.md`
- `.agent/workflows/wiki-query.md`
- `.agent/workflows/wiki-lint.md`

### Stack config and health checks

- `.llm-wiki/config.json`
- `.llm-wiki/package.json`
- `.llm-wiki/qmd-embed-state.json`
- `.brv/context-tree/.gitkeep`
- `scripts/check_llm_wiki_memory.ps1`
- `scripts/check_llm_wiki_memory.sh`
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
- `templates/`
- `scripts/`

## Manual prerequisites

The packet configures the stack, but two parts remain intentionally manual:

1. `pk-qmd` is bundled as a dependency of this packet and can also be installed directly from the custom fork.
2. BRV auth and GitVizz app wiring depend on your local credentials and GitHub App settings.

Use the installed helpers from the vault root when you want machine-level setup or verification:

- `scripts/setup_llm_wiki_memory.ps1`
- `scripts/setup_llm_wiki_memory.sh`
- `scripts/check_llm_wiki_memory.ps1`
- `scripts/check_llm_wiki_memory.sh`
- `scripts/qmd_embed_runner.mjs`

### 1. Install the custom `pk-qmd` fork

The canonical repo is:

- `https://github.com/kingkillery/pk-qmd`

If you already have the fork locally, use that checkout instead of recloning. On this machine the local path is:

- `C:\dev\Desktop-Projects\pk-qmd-main`

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

After `pk-qmd` is installed, wire the MCP config from the fork repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-pk-qmd-mcp-all.ps1
```

Key fork behavior this packet assumes:

- command name is `pk-qmd`
- shared MCP endpoint is `http://localhost:8181/mcp`
- the fork adds Gemini-backed multimodal commands such as `pk-qmd membed`, `pk-qmd msearch`, and `pk-qmd simage`

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

### Optional local setup helpers

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

What the setup helper now does:

- installs or verifies `pk-qmd`
- prefers the packet-local dependency manifest at `.llm-wiki/package.json`
- falls back to `kingkillery/pk-qmd` only if the local dependency path is unavailable
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

Run these from inside the target vault if you want the current directory used automatically.

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
- `LLM_WIKI_GITVIZZ_REPO_PATH=<optional local checkout path>`

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

Release assets are generated automatically by GitHub Actions from the checked-in root installers when a release is published. The release installers default to the release tag instead of `main`.

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

```bash
python3 installers/install_obsidian_agent_memory.py --vault "/path/to/Your Vault"
```

Optional flags:

```bash
python3 installers/install_obsidian_agent_memory.py \
  --vault "/path/to/Your Vault" \
  --targets claude,antigravity,codex,droid \
  --force
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
