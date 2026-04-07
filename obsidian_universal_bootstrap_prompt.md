# Universal bootstrap prompt for the llm-wiki-memory system

Paste this into Claude Code, Codex, Droid, Antigravity, or another terminal-capable coding agent.

```md
You are a senior developer-operator. Your job is to bootstrap the llm-wiki-memory system inside my existing Obsidian vault and install the repo-local agent files needed for Claude Code, Codex, Droid, and Antigravity-style workflows.

## Objective

Set up my vault as a persistent markdown knowledge base with:
- immutable raw sources
- a maintained wiki layer
- concise top-level guidance files
- reusable repo-local skills, workflows, and commands
- an explicit stack config for `pk-qmd`, `brv`, and `GitVizz`
- repeatable local verification scripts

Assume this is an implementation task, not a planning-only task.
Do the work.
Only stop for GUI downloads, browser sign-in, OS permission prompts, admin elevation, private-repo authentication, or destructive overwrite decisions.

## System model

The stack is:
- `pk-qmd` for source evidence and corpus retrieval
- `Byterover` (`brv`) for durable memory and recurring workflow knowledge
- `GitVizz` for repo graph and local web access

End users should experience one coherent intelligence surface. Do not make them manage raw tool choices unless they explicitly ask.

## Inputs

Use these variables and ask for them only if missing:
- `VAULT_PATH`: absolute path to my existing Obsidian vault
- `PROJECT_NAME`: default `llm-wiki`
- `INSTALL_TOOLS`: default `true`
- `INSTALL_OBSIDIAN`: default `false` if Obsidian is already installed, otherwise `true`
- `FORCE_OVERWRITE`: default `false`
- `GITVIZZ_FRONTEND_URL`: default `http://127.0.0.1:3000`
- `GITVIZZ_BACKEND_URL`: default `http://127.0.0.1:8003`
- `PK_QMD_MCP_URL`: default `http://127.0.0.1:8181/mcp`
- `PK_QMD_REPO_URL`: default `https://github.com/kingkillery/pk-qmd`

If a value is missing, infer it when safe.

## Important authoring constraint

Keep `AGENTS.md` and `CLAUDE.md` brief, directive, and operational.
They should guide the agent, not become long documentation essays.
Put larger procedures into skills, workflows, commands, config, and support files.

## Canonical file layout to install in the vault

### Shared root
- `AGENTS.md`
- `CLAUDE.md`

### Stack config and health checks
- `.llm-wiki/config.json`
- `.llm-wiki/package.json`
- `.llm-wiki/qmd-embed-state.json`
- `.brv/context-tree/.gitkeep`
- `scripts/check_llm_wiki_memory.ps1`
- `scripts/check_llm_wiki_memory.sh`
- `scripts/qmd_embed_runner.mjs`

### Vault content
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

### Claude Code
- `.claude/commands/wiki-ingest.md`
- `.claude/commands/wiki-query.md`
- `.claude/commands/wiki-lint.md`

### Codex
- `.agents/skills/llm-wiki-organizer/SKILL.md`
- `.agents/skills/llm-wiki-organizer/assets/system-prompt.md`
- `.agents/skills/llm-wiki-organizer/assets/tool-directives.md`
- `.agents/skills/llm-wiki-organizer/assets/output-contract.md`

### Droid
- root `AGENTS.md`
- do not invent extra Droid-only config unless clearly needed

### Antigravity
- `.agent/workflows/wiki-ingest.md`
- `.agent/workflows/wiki-query.md`
- `.agent/workflows/wiki-lint.md`

## What you must do

### 1. Verify or install tooling, if missing

Use official docs and package-manager installs where documented.
If a tool is already installed and working, do not reinstall it.

#### `pk-qmd`
- This packet should carry a direct dependency path to `pk-qmd`, so use the packet-local manifest first.
- Preferred source repo: `https://github.com/kingkillery/pk-qmd`
- First try the packet-local install:

```powershell
npm install --prefix .\.llm-wiki
.\.llm-wiki\node_modules\.bin\pk-qmd.cmd --help
```

- If the fork already exists locally, use that checkout instead of recloning.
- Fallback install from the fork checkout:

```powershell
git clone https://github.com/kingkillery/pk-qmd.git pk-qmd
cd pk-qmd
bun install
bun link
pk-qmd --help
```

- After installation, run the fork's MCP wiring helper if present:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-pk-qmd-mcp-all.ps1
```

#### Byterover
- macOS Apple Silicon / Linux: `curl -fsSL https://byterover.dev/install.sh | sh`
- Windows or macOS Intel: `npm install -g byterover-cli`
- Then authenticate with either `brv login --api-key <key>` or `BYTEROVER_API_KEY`

#### GitVizz
- frontend origin should be `http://localhost:3000/`
- backend origin should be `http://localhost:8003/`
- GitHub App config should use:
  - Homepage URL: `http://localhost:3000/`
  - Setup URL: `http://localhost:3000/`
  - Callback URL: `http://localhost:3000/api/auth/callback/github`

#### Common prerequisites
- Bun
- Node.js
- Python
- Git

## File content requirements

Write concise but useful versions of these files:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `.llm-wiki/config.json`
4. `scripts/check_llm_wiki_memory.ps1`
5. `scripts/check_llm_wiki_memory.sh`
6. `scripts/qmd_embed_runner.mjs`
7. `.claude/commands/wiki-ingest.md`
8. `.claude/commands/wiki-query.md`
9. `.claude/commands/wiki-lint.md`
10. `.agents/skills/llm-wiki-organizer/SKILL.md`
11. `.agents/skills/llm-wiki-organizer/assets/system-prompt.md`
12. `.agents/skills/llm-wiki-organizer/assets/tool-directives.md`
13. `.agents/skills/llm-wiki-organizer/assets/output-contract.md`
14. `.agent/workflows/wiki-ingest.md`
15. `.agent/workflows/wiki-query.md`
16. `.agent/workflows/wiki-lint.md`
17. `installers/install_obsidian_agent_memory.py`
18. `installers/install_obsidian_agent_memory.sh`

## Content rules

- Keep top-level instruction files short.
- Store stack endpoints and command names in `.llm-wiki/config.json`.
- Use `pk-qmd` for repo-specific evidence retrieval.
- Bootstrap a real QMD collection and embeddings for the vault, not just the CLI install.
- Use `brv` only for durable memory, preferences, and non-obvious workflow conventions.
- Initialize `.brv/config.json` when BRV is available.
- Prefer current source evidence over memory when they conflict.
- Keep logs append-only.
- Use markdown that works well in Obsidian.
- Do not overwrite user-authored content unless forced.

## Verification steps

After setup:
1. verify each installed CLI with a version check or executable lookup
2. verify the vault folders and key files exist
3. verify `.llm-wiki/config.json` exists and contains the stack endpoints
4. run the local installer in dry-run mode
5. run the local health check script
6. print a short operator report

## Required final report format

Return exactly these sections:

### Installed tools
- tool name
- version or status
- install method used

### Files created
- one bullet per file

### Files skipped
- explain why skipped

### Manual actions still required
- one bullet per action

### How to rerun
- exact command for macOS/Linux
- exact command for Windows PowerShell

### Notes
- brief caveats only

## Execution policy

- Proceed automatically for safe, reversible actions.
- Ask only for admin elevation, GUI confirmation, browser sign-in, private repo auth, or overwrite of existing user-authored files.
- If `pk-qmd` install is blocked by private repo access, continue with the vault structure, config, prompts, and verification scripts.
- If a single tool install is blocked, continue with the repo-local setup.

Begin now.
```
