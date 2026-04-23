# Documentation Audit — 2026-04-22

## Scope
Reviewed and updated the main user-facing and operator-facing documentation surfaces for correctness after the roadmap-driven memory upgrades.

Reviewed surfaces:

- `README.md`
- `QUICKSTART.md`
- `LLM_WIKI_MEMORY.md`
- `docs/rfc-memory-taxonomy.md`
- `deploy/cloudflare/README.md`

## QA Summary

### Passes
- Main install and quickstart flow is now documented consistently.
- Skill-index lifecycle is now documented as an automatic managed artifact rather than a manual maintenance burden.
- Cloudflare edge guidance now matches the actual Worker implementation in `deploy/cloudflare/mcp-edge-worker.js`.

### Issues Found and Fixed
1. **Missing auto-maintenance explanation for skill scoring artifacts**
   - Problem: docs described the retrieval/scoring surface, but not when `.llm-wiki/skill-index.json` is built or refreshed.
   - Fix: updated README, QUICKSTART, RFC, and vault guidance to state that setup/check build the index and runtime surfaces lazily refresh it when stale.

2. **Bootstrap surface list was incomplete**
   - Problem: README's generated script list omitted newer runtime scripts such as `build_skill_index.py`, `skill_trigger.py`, `auto_reducer_watcher.py`, and `dashboard_server.py`.
   - Fix: expanded the script inventory.

3. **Cloudflare guide was underspecified relative to the worker**
   - Problem: the guide did not clearly state that `ORIGIN_BASE_URL` should point to the origin root rather than `/mcp`, and it implied more `wrangler` config than the example file actually provides.
   - Fix: clarified `ORIGIN_BASE_URL`, explicitly documented optional `EDGE_API_TOKEN`, and noted that routes/custom domains must still be configured in Cloudflare.

## Remaining Notes
- The repo still contains many research/synthesis notes; this audit prioritized docs that affect installation, operation, retrieval behavior, and hosted-edge deployment.
- Future doc QA should re-run after any deployment-surface change or public routing change.
