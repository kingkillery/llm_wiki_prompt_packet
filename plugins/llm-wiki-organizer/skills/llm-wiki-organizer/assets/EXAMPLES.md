# Worked Examples

Each example shows the full arc of a skill invocation: input, classification, routing, files touched, response shape, and at least one process improvement applied.

---

## Example 1: Ingest a new source into an existing topic

### Input

> Ingest `raw/papers/attention-is-all-you-need.pdf` into the wiki. We already have a Transformers concept page.

### Task classification

`ingest`

### Routing

| Tool | Used? | Why |
|------|-------|-----|
| `pk-qmd` | Yes | Search for existing pages mentioning "attention" or "transformer" before creating anything new. |
| `brv` | No | No durable preference or prior decision relevant here. |
| `GitVizz` | No | No repo-topology question involved. |

### Files read

- `AGENTS.md`
- `LLM_WIKI_MEMORY.md`
- `.llm-wiki/config.json`
- `wiki/index.md`
- `wiki/log.md` (last 20 entries)
- `raw/papers/attention-is-all-you-need.pdf`
- `wiki/concepts/transformers.md` (found via pk-qmd)

### Files changed

- `wiki/sources/attention-is-all-you-need.md` (created)
- `wiki/concepts/transformers.md` (updated — added claims, citations, and cross-references)
- `wiki/entities/vaswani-et-al.md` (created — author entity page)
- `wiki/index.md` (added new source and entity entries)
- `wiki/log.md` (appended ingest entry)

### Response shape

```
Task type: ingest

Stack/config used:
- .llm-wiki/config.json defaults
- pk-qmd: searched "transformer" and "attention mechanism"

Files read:
- raw/papers/attention-is-all-you-need.pdf
- wiki/concepts/transformers.md
- wiki/index.md, wiki/log.md

Files changed:
- wiki/sources/attention-is-all-you-need.md (new)
- wiki/concepts/transformers.md (updated)
- wiki/entities/vaswani-et-al.md (new)
- wiki/index.md (updated)
- wiki/log.md (appended)

What changed:
- Source summary created with 12 key claims and 3 open questions
- Transformers concept page updated with self-attention mechanism details and citation
- Author entity page created with publication list stub

Unresolved questions / conflicts:
- Paper claims O(1) sequential operations for self-attention; existing wiki notes O(n) for recurrence but does not compare directly

Next best actions:
- Review wiki/concepts/transformers.md for completeness
- Consider creating a wiki/comparisons/attention-vs-recurrence.md page
```

### Process improvement applied

Searched for existing "transformer" pages before creating any new files. Found and updated the existing concept page instead of creating a duplicate.

---

## Example 2: Answer a question and file the answer back

### Input

> What routing rules does the wiki use for pk-qmd vs brv? File the answer into the wiki if it isn't already there.

### Task classification

`query`

### Routing

| Tool | Used? | Why |
|------|-------|-----|
| `pk-qmd` | Yes | Search for routing-related content across prompts and docs. |
| `brv` | Yes | Check if there are curated durable notes about routing conventions. |
| `GitVizz` | No | Not a repo-topology question. |

### Files read

- `AGENTS.md`
- `LLM_WIKI_MEMORY.md`
- `.llm-wiki/config.json`
- `wiki/index.md`
- `wiki/log.md` (last 10 entries)
- `prompts/00-system-prompt.md` (found via pk-qmd — contains routing policy)
- `plugins/llm-wiki-organizer/skills/llm-wiki-organizer/assets/tool-directives.md` (found via pk-qmd)

### Files changed

- `wiki/concepts/stack-routing-rules.md` (created — no existing page covered this)
- `wiki/index.md` (added entry)
- `wiki/log.md` (appended query entry)

### Response shape

```
Task type: query

Stack/config used:
- pk-qmd: searched "routing" and "pk-qmd vs brv"
- brv: queried "routing conventions" — returned one prior note confirming evidence > memory rule

Files read:
- prompts/00-system-prompt.md (routing policy section)
- plugins/.../tool-directives.md

Files changed:
- wiki/concepts/stack-routing-rules.md (new)
- wiki/index.md (updated)
- wiki/log.md (appended)

What changed:
- Created a durable routing-rules concept page summarizing pk-qmd, brv, and GitVizz decision criteria
- Cross-linked to LLM_WIKI_MEMORY.md as the authoritative source

Unresolved questions / conflicts:
- None — brv note and source evidence agree

Next best actions:
- Link from any entity or concept pages that reference tool routing
```

### Process improvement applied

Filed the synthesized answer back into the wiki as a concept page, since no existing page covered routing rules as a standalone topic. This makes the answer discoverable for future queries without re-running pk-qmd.

---

## Example 3: Lint the vault for duplicates and weak links

### Input

> Lint the wiki. Focus on duplicates and orphan pages.

### Task classification

`lint`

### Routing

| Tool | Used? | Why |
|------|-------|-----|
| `pk-qmd` | Yes | Searched for near-duplicate content across wiki pages. |
| `brv` | No | No durable memory needed for structural audit. |
| `GitVizz` | No | Not a repo-topology question. |

### Files read

- `AGENTS.md`
- `wiki/index.md`
- `wiki/log.md` (last 30 entries)
- All pages under `wiki/` (18 pages total)

### Files changed

- `wiki/concepts/llm-agents.md` (merged content from duplicate `wiki/concepts/ai-agents.md`)
- `wiki/concepts/ai-agents.md` (deleted after merge — user confirmed)
- `wiki/entities/openai.md` (added backlinks — was orphaned)
- `wiki/index.md` (removed duplicate entry, added missing backlink)
- `wiki/log.md` (appended lint entry)

### Response shape

```
Task type: lint

Stack/config used:
- pk-qmd: searched for overlapping content across wiki/concepts/

Files read:
- All 18 wiki pages

Files changed:
- wiki/concepts/llm-agents.md (merged duplicate content)
- wiki/concepts/ai-agents.md (deleted after user confirmation)
- wiki/entities/openai.md (added backlinks)
- wiki/index.md (cleaned up)
- wiki/log.md (appended)

What changed:
- Merged ai-agents.md into llm-agents.md (90% content overlap)
- Added 3 backlinks to orphaned openai.md entity page
- Removed stale index entry for deleted page

Unresolved questions / conflicts:
- wiki/syntheses/prompt-engineering-overview.md has only 2 sentences — recommend expanding or merging

Next best actions:
- Expand or merge the thin synthesis page
- Re-run lint after next ingest to catch new orphans
```

### Process improvement applied

Asked for user confirmation before deleting the duplicate page, since deletion is irreversible. Merged content first, then deleted, to avoid data loss.

---

## Example 4: Resolve a conflict where brv memory disagrees with source evidence

### Input

> What embedding model does pk-qmd use? I think we switched recently.

### Task classification

`query`

### Routing

| Tool | Used? | Why |
|------|-------|-----|
| `pk-qmd` | Yes | Check current config and source docs for the active embedding model. |
| `brv` | Yes | Queried for prior decision about embedding model choice. |
| `GitVizz` | No | Not a topology question. |

### Files read

- `.llm-wiki/config.json`
- `LLM_WIKI_MEMORY.md`
- `wiki/index.md`
- `wiki/entities/pk-qmd.md`
- `package.json` (found via pk-qmd — contains pk-qmd dependency version)

### Files changed

- `wiki/entities/pk-qmd.md` (updated embedding model reference, added conflict note)
- `wiki/log.md` (appended query entry with conflict flag)

### Response shape

```
Task type: query

Stack/config used:
- pk-qmd: searched "embedding model" in config and docs
- brv: queried "pk-qmd embedding model" — returned note saying "text-embedding-ada-002"

Files read:
- .llm-wiki/config.json
- LLM_WIKI_MEMORY.md (documents current default)
- wiki/entities/pk-qmd.md

Files changed:
- wiki/entities/pk-qmd.md (updated)
- wiki/log.md (appended)

What changed:
- Updated pk-qmd entity page: embedding model is now text-embedding-3-small per current LLM_WIKI_MEMORY.md
- Added conflict note: brv still records text-embedding-ada-002 from an earlier decision
- Flagged brv memory as stale

Unresolved questions / conflicts:
- brv memory says "text-embedding-ada-002" but current source says "text-embedding-3-small"
- Resolution: current source evidence wins per system prompt rules
- Recommend curating brv to update the stale entry

Next best actions:
- Run `brv curate` to update the embedding model memory
- Verify embedding dimensions are consistent across existing indexes
```

### Process improvement applied

Explicitly flagged the brv/source conflict in both the wiki page and log entry instead of silently overwriting. This makes the conflict visible to future queries and to the user.

---

## Example 5: Use pk-qmd first, then GitVizz, when the target area is unknown

### Input

> Where does the installer validate the vault path? I need to understand the validation flow.

### Task classification

`query`

### Routing

| Tool | Used? | Why |
|------|-------|-----|
| `pk-qmd` | Yes (first) | Broad search for "vault path" and "validate" — target file unknown. |
| `GitVizz` | Yes (second) | After pk-qmd located `installers/install_obsidian_agent_memory.py`, used GitVizz to map surrounding file dependencies and call graph. |
| `brv` | No | No durable memory relevant. |

### Files read

- `AGENTS.md`
- `wiki/index.md`
- `installers/install_obsidian_agent_memory.py` (found via pk-qmd)
- `install.ps1` and `install.sh` (found via GitVizz dependency context)

### Files changed

- None — query-only, answer does not create durable wiki value beyond what the code already documents.

### Response shape

```
Task type: query

Stack/config used:
- pk-qmd: searched "vault path validate" — found install_obsidian_agent_memory.py
- GitVizz: mapped installer dependency graph from installers/ directory

Files read:
- installers/install_obsidian_agent_memory.py
- install.ps1
- install.sh

Files changed:
- (none — answer is code-specific, not wiki-durable)

What changed:
- (no wiki changes)

Unresolved questions / conflicts:
- None

Next best actions:
- If validation logic needs to change, the entry point is install_obsidian_agent_memory.py lines 45-72
```

### Process improvement applied

Used the pk-qmd-then-GitVizz sequence: pk-qmd located the file when the target was unknown, then GitVizz mapped the surrounding context. Did not file the answer into the wiki because it describes current code behavior that is better read directly from source.
