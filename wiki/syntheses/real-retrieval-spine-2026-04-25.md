# Real Retrieval Spine (2026-04-25)

## Summary

The packet now has a v2 retrieval spine for agentic harness bootstrap:

- `llm-wiki-packet context` keeps default startup context compact and local-first.
- `llm-wiki-packet context --mode deep` explicitly expands through source and preference retrieval planes.
- `llm-wiki-packet evidence` can route across `source`, `skills`, `preference`, `graph`, and `local` planes.
- Every retrieval result carries plane, retrieval method, status, source, locator, snippet, score, confidence, provenance, stale flag, contradiction list, and error fields.
- External tools degrade to local/file/config fallbacks instead of blocking task completion.

## Routing Contract

Default context uses instructions, skill index suggestions, recent wiki lessons, local source search, preference files, and GitVizz configuration hints. It does not invoke broad source, BRV, or GitVizz API retrieval by default.

Explicit evidence retrieval uses this order when `--plane all` is selected:

1. `source`: configured `pk-qmd`; fallback to local source search.
2. `skills`: configured skill index.
3. `preference`: `brv query --format json`; fallback to preference files.
4. `graph`: GitVizz HTTP API; fallback to GitVizz config and local code hints.
5. `local`: deterministic local lexical search.

Source evidence remains higher priority than BRV preference memory when they conflict.

## Validation

- `python -m py_compile support\scripts\llm_wiki_packet.py installers\install_obsidian_agent_memory.py`
- `python -m pytest tests\test_llm_wiki_packet.py tests\test_install_obsidian_agent_memory.py -q` -> `31 passed`
- `python support\scripts\llm_wiki_packet.py context --task "bootstrap verification" --json`
- `python support\scripts\llm_wiki_packet.py evidence --query "bootstrap verification" --json --timeout-sec 5`

The smoke run confirmed that default context stays compact while explicit evidence returns degraded local fallbacks when `pk-qmd` does not emit JSON and BRV times out.
