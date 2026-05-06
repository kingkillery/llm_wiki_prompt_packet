# Spec: Obsidian Canonical Wiki Provider

## Status

Draft implementation spec.

## Related

- PRD: `docs/prd-obsidian-canonical-wiki-provider.md`
- System contract: `support/SYSTEM_CONTRACT.md`
- Runtime config builder: `installers/install_obsidian_agent_memory.py`
- Runtime setup/check logic: `support/scripts/llm_wiki_memory_runtime.py`
- Obsidian MCP wrapper: `support/scripts/llm_wiki_obsidian_mcp.py`

## Design Summary

Add a canonical wiki-provider layer above the existing Obsidian MCP transport.

The current `obsidian` config describes how to start the vault transport. The new `wiki_layer` config describes how the packet should treat the vault as a maintained semantic wiki.

```text
agent behavior
  -> wiki provider interface
    -> Obsidian wiki provider
      -> transport adapter
        -> mcpvault / mcp-obsidian / direct file I/O
```

## Config Model

Add `wiki_layer` to `.llm-wiki/config.json`.

```json
{
  "wiki_layer": {
    "provider": "obsidian",
    "behavior_layer": "agent-cli-obsidian",
    "behavior_layer_repo": "https://github.com/kingkillery/agent-cli-obsidian",
    "transport": "mcpvault",
    "alternate_transport": "mcp-obsidian",
    "vault_path": ".",
    "raw_path": ".raw",
    "wiki_path": "wiki",
    "index_path": "wiki/index.md",
    "log_path": "wiki/log.md",
    "hot_cache_path": "wiki/hot.md",
    "folders": {
      "sources": "wiki/sources",
      "concepts": "wiki/concepts",
      "entities": "wiki/entities",
      "questions": "wiki/questions",
      "syntheses": "wiki/syntheses",
      "decisions": "wiki/decisions",
      "sessions": "wiki/sessions",
      "meta": "wiki/meta"
    },
    "note_types": ["synthesis", "concept", "source", "decision", "session"],
    "research_note_types": ["source", "entity", "concept", "question", "synthesis"],
    "offer_save_for_substantial_answers": true,
    "deep_research_save_default": true,
    "update_existing_before_create": true,
    "direct_file_fallback": true,
    "log_transport_fallback": true
  }
}
```

### Compatibility Rules

- If `wiki_layer` is absent, default to `provider = "obsidian"` when `obsidian.vault_path` is configured.
- If `wiki_layer.vault_path` is absent, use `obsidian.vault_path`, then `memory_base.vault_path`, then workspace root.
- Existing `obsidian` config remains the MCP transport config.
- `wiki_layer.transport` should not be used to infer package names directly; it selects the adapter.

## Runtime Defaults

Add defaults to `support/scripts/llm_wiki_memory_runtime.py`:

- `DEFAULT_WIKI_PROVIDER = "obsidian"`
- `DEFAULT_WIKI_BEHAVIOR_LAYER = "agent-cli-obsidian"`
- `DEFAULT_WIKI_BEHAVIOR_REPO = "https://github.com/kingkillery/agent-cli-obsidian"`
- default folder map
- default note taxonomy

Add runtime keys:

- `wiki_provider`
- `wiki_vault_path`
- `wiki_raw_path`
- `wiki_path`
- `wiki_index_path`
- `wiki_log_path`
- `wiki_hot_cache_path`
- `wiki_folders`
- `wiki_transport`
- `wiki_note_types`
- `wiki_research_note_types`
- `wiki_deep_research_save_default`

## Installer Changes

Update `build_stack_config()` in `installers/install_obsidian_agent_memory.py`:

- keep existing `obsidian` section
- add new `wiki_layer` section
- preserve existing project values on refresh

Update tests:

- assert new installs include `wiki_layer`
- assert refresh preserves custom `wiki_layer` fields
- assert missing section is backfilled without overwriting existing values

## Wiki Provider Interface

Create `support/scripts/llm_wiki_provider.py`.

Suggested API:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class WikiWriteResult:
    path: str
    action: str  # created | updated
    transport: str

class WikiProvider:
    def read(self, path: str) -> str: ...
    def write(self, path: str, content: str) -> WikiWriteResult: ...
    def exists(self, path: str) -> bool: ...
    def search(self, query: str, *, limit: int = 10) -> list[dict]: ...
    def move(self, old_path: str, new_path: str) -> None: ...
    def tag(self, path: str, tags: list[str]) -> None: ...
```

### Adapter Implementations

M1 can ship direct file adapter only, with MCP hooks as extension points.

Adapters:

- `DirectFileWikiProvider`
- `McpVaultWikiProvider`
- `ObsidianRestWikiProvider`

Selection:

1. if configured MCP adapter is available, use it
2. else if REST adapter is configured, use it
3. else if `direct_file_fallback = true`, use direct file adapter
4. else fail readiness

## Save Workflow

Create `support/scripts/llm_wiki_save.py`.

CLI:

```text
python scripts/llm_wiki_save.py \
  --workspace <path> \
  --title <title> \
  --type synthesis \
  --body-file <path> \
  --source <source-url-or-wikilink> \
  --tag research \
  --related "[[Existing Page]]"
```

### Inputs

- `title`
- `note_type`
- `body`
- `sources`
- `related`
- `tags`
- `question`
- `confidence`
- `mode` (`create-or-update`, `create-only`, `update-only`)

### Path Selection

Map note type to folder:

| Type | Folder |
|---|---|
| source | `wiki/sources` |
| concept | `wiki/concepts` |
| entity | `wiki/entities` |
| question | `wiki/questions` |
| synthesis | `wiki/syntheses` preferred, fallback `wiki/questions` if configured |
| decision | `wiki/decisions` preferred, fallback `wiki/meta` |
| session | `wiki/sessions` preferred, fallback `wiki/meta` |

### Duplicate Detection

Use these candidate keys:

- normalized title slug
- frontmatter `title`
- frontmatter `aliases`
- exact source URL
- exact question
- canonical keys if supplied

If a candidate exists, update it instead of creating a duplicate.

### Frontmatter

Minimum:

```yaml
---
type: synthesis
title: "Title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - research
status: developing
related: []
sources: []
---
```

Additional:

- question pages: `question`, `answer_quality`
- source pages: `source_type`, `url`, `confidence`, `key_claims`
- decision pages: `decision_date`, `decision_status`
- concept pages: `domain`, `aliases`

### Index Update

Add or update one line under the matching section in `wiki/index.md`.

If section is missing, create it.

Example:

```markdown
## Syntheses
- [[Research Retrieval Patterns]]: source-backed synthesis (status: developing)
```

### Log Update

Prepend:

```markdown
## [YYYY-MM-DD] save | Title
- Type: synthesis
- Location: wiki/syntheses/Title.md
- Action: created
- Sources: [[Source 1]]
```

### Hot Cache Update

Update `wiki/hot.md` with:

- last updated timestamp
- key recent facts
- created/updated pages
- active open questions

Keep under roughly 500 words.

## Research Save Workflow

Create a higher-level mode in `llm_wiki_save.py` or a separate `llm_wiki_research_save.py`.

Inputs:

- topic
- source records
- extracted entities
- extracted concepts
- synthesis body
- open questions

Outputs:

- source pages
- entity pages
- concept pages
- question page if a user question exists
- synthesis page
- index/log/hot updates

M1 can specify this workflow without fully implementing it. M2 should implement basic synthesis-only save. M4 should implement multi-page research save.

## Health Check Integration

Update `support/scripts/llm_wiki_memory_runtime.py`.

Add `verify_wiki_layer(runtime, summary, failures, warnings)`.

Checks:

- `wiki_provider == "obsidian"` or known provider
- `wiki_vault_path` exists
- configured wiki paths are inside vault path
- `.raw/` and `wiki/` exist or can be created
- `index`, `log`, `hot` exist or can be created
- selected transport is available, or direct file fallback is enabled
- note taxonomy is non-empty

Suggested statuses:

- PASS: transport or fallback writable and required files present
- WARN: MCP unavailable but direct file fallback works
- FAIL: no writable wiki path

## Commands

Add command docs:

- `.claude/commands/wiki-save.md`
- `.agent/workflows/wiki-save.md`

Command behavior:

1. inspect current answer/session
2. classify note type
3. ask for title if missing
4. call save workflow or follow equivalent steps
5. report created/updated paths

Avoid hijacking `/save` initially because other ecosystems may already define it.

## Tests

### Unit Tests

Add `tests/test_llm_wiki_provider.py`:

- direct file read/write
- path traversal rejection
- path normalization
- missing file behavior
- move fallback warning behavior

Add `tests/test_llm_wiki_save.py`:

- creates synthesis note
- updates existing note
- writes frontmatter
- updates index
- prepends log
- updates hot cache
- maps note types to folders
- preserves sources and related links

Update `tests/test_install_obsidian_agent_memory.py`:

- generated config includes `wiki_layer`
- refresh preserves custom `wiki_layer`
- required paths include `wiki/hot.md`

Update `tests/test_llm_wiki_memory_runtime.py`:

- runtime defaults include wiki layer values
- health check passes with direct file fallback
- health check warns when MCP missing but fallback exists
- health check fails when vault is not writable

## Security and Safety

- Reject paths that resolve outside the configured vault.
- Never edit `.raw/` except when explicitly ingesting/copying user-provided sources.
- Do not overwrite existing notes unless update mode is selected.
- For move/rename, use Obsidian-aware transport when available; otherwise pause or warn.
- Do not persist secrets from chat into wiki notes.

## Migration Plan

1. Add config and runtime defaults.
2. Add readiness checks.
3. Add direct file provider.
4. Add save workflow.
5. Add command docs.
6. Add MCP/REST adapters.
7. Add optional `agent-cli-obsidian` skill import.

## Backward Compatibility

- Existing installs without `wiki_layer` keep working.
- `obsidian` config remains unchanged for MCP startup.
- Direct file fallback preserves current packet behavior.
- Existing `wiki/index.md` and `wiki/log.md` content is not replaced.

## Completion Gates

Implementation is complete when:

- `.llm-wiki/config.json` has `wiki_layer` on new installs
- runtime defaults expose wiki layer keys
- health check reports wiki provider readiness
- save workflow creates/updates notes and index/log/hot
- generated agent docs instruct offer-save and deep-research default-save
- tests cover config, health, provider, and save workflow
- docs explain `llm_wiki_prompt_packet` / `agent-cli-obsidian` / transport layering
