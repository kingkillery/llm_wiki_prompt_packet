# Obsidian Wiki Update Setup Validation (2026-04-24)

## Result

The packet is now set up to leave wiki updates and improvements through the configured markdown wiki flow, with Obsidian MCP as the preferred scribing path and direct file I/O as the documented fallback.

## Validated Surfaces

- `.mcp.json` declares `pk-qmd`, `llm-wiki-skills`, `obsidian`, and `brv`.
- The configured Kade-HQ vault path exists at `C:\dev\Desktop-Projects\Helpful-Docs-Prompts\VAULTS-OBSIDIAN\Kade-HQ`.
- `support/scripts/llm_wiki_obsidian_mcp.py` now honors `OBSIDIAN_VAULT_PATH`, so the Obsidian MCP wrapper no longer silently falls back to the repo root when launched from `.mcp.json`.
- `scripts/check_llm_wiki_memory.ps1` and `scripts/check_llm_wiki_memory.sh` are present again, matching the documented installed helper surface.
- `scripts/run_llm_wiki_agent.ps1`, `scripts/run_llm_wiki_agent.sh`, and `scripts/run_llm_wiki_agent.cmd` are present again, so agent launch and failure capture checks pass.
- Windows command resolution now avoids broken shell shims by falling back from unusable npm-generated `pk-qmd.cmd` wrappers to the managed checkout entrypoint at `.llm-wiki/tools/pk-qmd/dist/cli/qmd.js`.

## Health Check

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_llm_wiki_memory.ps1 -VerifyOnly -SkipGitvizzStart
```

Observed result:

- `pk-qmd`: reachable via managed checkout fallback.
- `brv`: reachable; provider connected as `openrouter`.
- Skill index: current.
- Agent runtimes: `claude`, `codex`, `droid`, and `pi` detected.
- GitVizz: configured but not currently reachable at `http://localhost:3000` or `http://localhost:8003`; endpoint-only mode remains allowed.

## Caveat

This validates wiki-update readiness, not a strict append-only vault policy. The current repo rules still allow small reversible edits and prefer updating existing pages. A separate append-only gate could be added later for selected vault log paths, but applying a global pre-commit line-removal blocker to this repo would interfere with normal code maintenance.
