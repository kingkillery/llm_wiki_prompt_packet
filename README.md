# LLM Wiki Prompt Packet

This packet turns the LLM Wiki idea into installable markdown prompts and a cross-tool installer for an Obsidian vault.

## What is included

### Root prompts
- `obsidian_universal_bootstrap_prompt.md` — universal implementation prompt for bootstrapping a vault and agent setup
- `temp-git-deployment.md` — deployment prompt for publishing the packet safely with hosted installers

### Packet prompts
- `prompts/00-system-prompt.md` — full maintainer contract
- `prompts/01-AGENTS.md` — brief root instructions for tools that read `AGENTS.md`
- `prompts/02-CLAUDE.md` — brief root instructions for Claude Code
- `prompts/03-codex-skill-SKILL.md` — Codex skill for explicit or implicit invocation
- `prompts/04-tool-directives.md` — compact operational directives
- `prompts/05-output-contract.md` — compact reporting contract
- `prompts/06-antigravity-ingest-workflow.md` — Antigravity workflow
- `prompts/07-antigravity-query-workflow.md` — Antigravity workflow
- `prompts/08-antigravity-lint-workflow.md` — Antigravity workflow
- `prompts/09-claude-command-ingest.md` — Claude Code command content
- `prompts/10-claude-command-query.md` — Claude Code command content
- `prompts/11-claude-command-lint.md` — Claude Code command content

### Installers
- `installers/install_obsidian_agent_memory.py` — installs the packet into an Obsidian vault
- `installers/install_obsidian_agent_memory.sh` — shell wrapper for the Python installer
- `installers/install_obsidian_agent_memory.ps1` — PowerShell wrapper for the Python installer

## Canonical vault targets written by the installer

### Shared root
- `AGENTS.md`
- `CLAUDE.md`

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

### Droid
- uses the same root `AGENTS.md`

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

## Installer usage

Example:

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

## Assumptions

- Your Obsidian vault is also the working directory for your coding agents.
- Brief instructions belong in `AGENTS.md` and `CLAUDE.md`; longer operational material lives in skills, workflows, and command files.
- The packet is intentionally conservative about tool-specific proprietary config.
