# Universal bootstrap prompt for an Obsidian organizer / memory system

Paste this into Claude Code, Codex, Droid, Antigravity, or another terminal-capable coding agent.

```md
You are a senior developer-operator. Your job is to bootstrap an Obsidian-based organizer / memory system inside my existing vault and install the repo-local agent files needed for Claude Code, Codex, Droid, and Antigravity-style workflows.

## Objective

Set up my vault as a persistent markdown knowledge base with:
- immutable raw sources
- a maintained wiki layer
- concise top-level guidance files
- reusable repo-local skills / workflows / commands
- a repeatable local installer script

Assume this is an implementation task, not a planning-only task.
Do the work.
Only stop for GUI downloads, browser sign-in, OS permission prompts, admin elevation, or destructive overwrite decisions.

## Inputs

Use these variables and ask for them only if missing:
- `VAULT_PATH`: absolute path to my existing Obsidian vault
- `PROJECT_NAME`: default `llm-wiki`
- `INSTALL_TOOLS`: default `true`
- `INSTALL_OBSIDIAN`: default `false` if Obsidian is already installed, otherwise `true`
- `FORCE_OVERWRITE`: default `false`

If a value is missing, infer it when safe.

## Important authoring constraint

Keep `AGENTS.md` and `CLAUDE.md` brief, directive, and operational.
They should guide the agent, not become long documentation essays.
Put larger procedures into skills, workflows, commands, or support files.

## Canonical file layout to install in the vault

### Shared root
- `AGENTS.md`
- `CLAUDE.md`

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
- do not invent extra Droid-only config unless it is clearly needed

### Antigravity
- `.agent/workflows/wiki-ingest.md`
- `.agent/workflows/wiki-query.md`
- `.agent/workflows/wiki-lint.md`

### Local installer
- `scripts/install_obsidian_agent_memory.py`
- `scripts/install_obsidian_agent_memory.sh`
- optional Windows wrapper: `scripts/install_obsidian_agent_memory.ps1`

## What you must do

### 1) Verify or install tooling, if missing

Use official docs and package-manager installs where documented.
If a tool is already installed and working, do not reinstall it.

#### Obsidian
- Download page: https://obsidian.md/download
- Install help: https://obsidian.md/help/install

#### Claude Code
- Quickstart: https://code.claude.com/docs/en/quickstart
- Setup / system requirements: https://code.claude.com/docs/en/setup
- Memory / `CLAUDE.md`: https://code.claude.com/docs/en/memory
- `.claude` directory: https://code.claude.com/docs/en/claude-directory
- Skills and commands docs: https://code.claude.com/docs/en/skills

#### Codex
- Quickstart: https://developers.openai.com/codex/quickstart
- CLI: https://developers.openai.com/codex/cli
- Windows guidance: https://developers.openai.com/codex/windows
- `AGENTS.md`: https://developers.openai.com/codex/guides/agents-md/
- Skills: https://developers.openai.com/codex/skills/

#### Droid / Factory
- CLI quickstart: https://docs.factory.ai/cli/getting-started/quickstart
- CLI overview: https://docs.factory.ai/cli/getting-started/overview
- `AGENTS.md` compatibility: https://docs.factory.ai/cli/configuration/agents-md
- Settings: https://docs.factory.ai/cli/configuration/settings

#### Antigravity
- Home / downloads: https://antigravity.google
- Docs: https://antigravity.google/docs
- Getting started codelab: https://codelabs.developers.google.com/getting-started-google-antigravity

#### Common prerequisites
- Node.js: https://nodejs.org/en/download
- npm docs: https://docs.npmjs.com/downloading-and-installing-node-js-and-npm/
- Git: https://git-scm.com/install/

## OS-specific install behavior

### macOS
- Obsidian: install from the official download page if missing.
- Claude Code: `curl -fsSL https://claude.ai/install.sh | bash`
- Codex: `brew install codex` if Homebrew is present, otherwise `npm install -g @openai/codex`
- Droid: `curl -fsSL https://app.factory.ai/cli | sh`
- Antigravity: use the official macOS download and continue with vault setup if GUI confirmation is needed.

### Windows
- Obsidian: install from the official download page if missing.
- Claude Code PowerShell: `irm https://claude.ai/install.ps1 | iex`
- Claude Code WinGet alternative: `winget install Anthropic.ClaudeCode`
- Codex: `npm install -g @openai/codex`
- Droid: use the official current Windows path from Factory docs; do not invent an undocumented command
- Antigravity: use the official Windows download and continue with vault setup if GUI confirmation is needed.

### Linux
- Obsidian: prefer `flatpak install flathub md.obsidian.Obsidian`; otherwise use AppImage or Snap from official Obsidian help.
- Claude Code: `curl -fsSL https://claude.ai/install.sh | bash`
- Codex: `npm install -g @openai/codex`
- Droid: `curl -fsSL https://app.factory.ai/cli | sh`
- Antigravity: use the official Linux-compatible distribution if available; continue with vault setup even if install must be finished manually.

## File content requirements

Write concise but useful versions of these prompt files:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `.claude/commands/wiki-ingest.md`
4. `.claude/commands/wiki-query.md`
5. `.claude/commands/wiki-lint.md`
6. `.agents/skills/llm-wiki-organizer/SKILL.md`
7. `.agents/skills/llm-wiki-organizer/assets/system-prompt.md`
8. `.agents/skills/llm-wiki-organizer/assets/tool-directives.md`
9. `.agents/skills/llm-wiki-organizer/assets/output-contract.md`
10. `.agent/workflows/wiki-ingest.md`
11. `.agent/workflows/wiki-query.md`
12. `.agent/workflows/wiki-lint.md`
13. `scripts/install_obsidian_agent_memory.py`
14. `scripts/install_obsidian_agent_memory.sh`

## Content rules

- Keep top-level instruction files short.
- Put detailed operating procedures into skills, workflows, commands, and support files.
- Preserve the core model: immutable raw sources, maintained wiki, schema-guided behavior.
- Prefer updating existing pages over duplicating them.
- Surface contradictions and uncertainty explicitly.
- Keep logs append-only.
- Use markdown that works well in Obsidian.
- Use relative paths inside the vault whenever possible.
- Do not overwrite user-authored content unless forced.

## Verification steps

After setup:
1. verify each installed CLI with a version check or executable lookup
2. verify the vault folders and key files exist
3. verify `wiki/index.md` and `wiki/log.md` exist
4. run the local installer in dry-run mode
5. print a short operator report

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
- Ask only for admin elevation, GUI confirmation, browser sign-in, or overwrite of existing user-authored files.
- If a single tool install is blocked, continue with the vault structure and repo-local agent files.
- If current official docs conflict with an expected command, trust the docs and adapt.

Begin now.
```
