# Quickstart

Zero to a wired repo with the full stack.

## One command

**PowerShell (Windows):**
```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.ps1))) -WireRepo
```

**Shell (macOS / Linux):**
```bash
curl -fsSL https://raw.githubusercontent.com/kingkillery/llm_wiki_prompt_packet/main/install.sh | bash -s -- --wire-repo
```

That command:

1. Runs **preflight** to detect missing tools (Python, Git, Node, curl) and prints platform-specific install hints before touching disk.
2. Lays the packet into the current directory as a workspace.
3. Installs the harness skill surfaces (`kade-hq`, `gstack`, `g-kade`).
4. **Wires global Claude config** - writes the LLM Wiki section into `~/.claude/CLAUDE.md` and copies `wiki-{ingest,query,lint,skill}.md` into `~/.claude/commands/`, so every future Claude session can call `/wiki-query`, `/wiki-ingest`, `/wiki-skill`, `/wiki-lint`.
5. Runs the **health check** and reports green/red.

## Verify

```bash
# macOS / Linux
bash ./scripts/check_llm_wiki_memory.sh
```
```powershell
# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_llm_wiki_memory.ps1
```

## Common flags

| Flag | What it does |
|---|---|
| `--wire-repo` / `-WireRepo` | Wire the current directory as a workspace (the one-command path) |
| `--mode packet` / `-Mode packet` | Install into an Obsidian vault instead of a workspace |
| `--no-global-wire` / `-NoGlobalWire` | Skip writing `~/.claude/CLAUDE.md` and global commands |
| `--skip-preflight` (env: `LLM_WIKI_SKIP_PREFLIGHT=1`) | Bypass tool detection |
| `--force` / `-Force` | Overwrite existing files |

For the full flag set: `bash install.sh --help` or `install.ps1 -Help`.

## Optional credentials

Both are optional. The health check warns when they are missing.

- `BYTEROVER_API_KEY` - enables `brv query` / `brv curate` (durable memory plane)
- `GEMINI_API_KEY` - enables `pk-qmd membed` / `msearch` (multimodal retrieval)

## Next

- Docker, GCP VM, Cloudflare edge: see [`README.md`](README.md).
- Architecture: [`SYSTEM_CONTRACT.md`](SYSTEM_CONTRACT.md).
- Per-vault agent rules: [`LLM_WIKI_MEMORY.md`](LLM_WIKI_MEMORY.md).
