# Installers (internal)

These Python/shell/PowerShell installers are the implementation layer. **Do not invoke them directly** unless you know exactly what you are doing.

For the user-facing one-command install, use the **project root** entrypoints:

- `install.sh --wire-repo` (macOS / Linux / Git Bash)
- `install.ps1 -WireRepo` (Windows PowerShell)

Or pipe from GitHub - see [`../README.md`](../README.md) > Quick Install.

| File | Purpose |
|---|---|
| `install_obsidian_agent_memory.{py,sh,ps1}` | Vault installer. Invoked by root installers in `packet` mode. |
| `install_g_kade_workspace.{py,sh,ps1}` | Workspace installer. Invoked by root installers in `g-kade` mode (set by `--wire-repo`). |
| `preflight.py` | Tool-detection preflight. Runs before any state change; exits non-zero with platform-specific install hints when a required tool is missing. |
| `wire_global_claude.py` | Idempotent global Claude wiring: writes the LLM Wiki section into `~/.claude/CLAUDE.md` and copies `wiki-*.md` commands into `~/.claude/commands/`. |
