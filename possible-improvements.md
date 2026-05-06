# Possible Improvements

These are candidate improvements for `llm_wiki_prompt_packet` gathered during comparison against adjacent wiki/Obsidian agent projects. Treat this as a backlog, not a commitment.

## Living Overview

- Add `wiki/overview.md` as a maintained high-level synthesis of the repo/vault.
- Keep `wiki/index.md` as navigation and `wiki/log.md` as chronology, but use `overview.md` for durable "what this workspace is and what we currently know."

## Conflict-Aware Saves

- Before saving a durable note, search related existing notes.
- If the new claim conflicts with prior knowledge, do not silently overwrite.
- Add one of:
  - `contradicts:` frontmatter
  - `supersedes:` frontmatter
  - a dated "Possible Conflict" section
  - a user prompt when the conflict affects an active decision

## Wiki Knowledge Graph

- Add optional graph artifacts separate from repo topology:
  - `graph/graph.json`
  - `graph/graph.html`
- Extract explicit `[[wikilinks]]`.
- Optionally infer semantic edges and label edge provenance:
  - `EXTRACTED`
  - `INFERRED`
  - `AMBIGUOUS`
- Cache graph builds by source file hash.
- Add a graph mode for Karpathy-style LLM wikis:
  - parse `wiki/index.md`
  - extract explicit wikilinks and folder categories
  - optionally extract entities, claims, and implicit relationships from article pages
  - cluster related notes into communities for navigation
- Prefer "graphs that teach" over ornamental graphs: every node should expose a summary, evidence, links, and why it matters.

## Guided Wiki Tours

- Generate guided tours for a repo or vault:
  - "read these pages first"
  - "understand this subsystem in this order"
  - "follow this decision trail"
- Order tours by dependency or evidence chain, not alphabetical page order.
- Add tours as markdown artifacts under:
  - `wiki/tours/`
  - or `wiki/meta/tours/`
- Use tours for onboarding, project handoff, and post-research synthesis.

## Diff Impact Analysis

- Add optional "wiki impact" analysis for code or note changes.
- Given a git diff, identify:
  - affected wiki pages
  - stale decisions
  - changed source assumptions
  - skills that may need updates
  - downstream concepts/entities to review
- Emit a short report before commit:
  - `wiki/meta/diff-impact.md`
  - or `.llm-wiki/reports/diff-impact-<date>.md`

## Obsidian Symlink Mode

- Keep direct vault writes as the default.
- Add an advanced option where repo-local `wiki/` is symlinked into the configured Obsidian vault.
- Make this opt-in because symlinks can confuse portability, backups, and cross-platform setups.

## Multi-Format Raw Ingest

- Formalize a pipeline:
  - `raw/imports/`
  - `raw/converted/`
  - `wiki/sources/`
- Support optional PDF/DOCX/PPTX/XLSX/HTML conversion before source-note creation.
- Prefer optional dependencies so the base packet stays lightweight.

## Compiler-Style Wiki Pipeline

- Treat wiki generation as an incremental compile step:
  - raw sources in
  - normalized source records
  - concept/entity pages
  - saved query pages
  - index/overview/hot cache
  - lint/status output
- Track per-source hashes and last compile times so unchanged sources are not reprocessed.
- Store compile state under:
  - `.llm-wiki/compile-state.json`
  - or `.llm-wiki/state/wiki-compile.json`
- Add a status command that reports:
  - source count
  - page count
  - pending changed sources
  - orphans
  - broken links
  - stale pages
- Add a compile command that returns structured counts, slugs, warnings, and errors.

## Saved Query Pages

- Add `wiki/queries/` for high-value answered questions.
- When a query answer is durable, save it as a query page and include it in index/retrieval.
- Query pages should link back to evidence pages and can later be promoted into synthesis/concept/decision notes.
- This prevents repeated questions from rediscovering the same answer.

## Stronger Wiki Lint

- Promote lint checks beyond formatting:
  - orphan pages
  - broken wikilinks
  - missing entity pages
  - duplicate notes
  - unresolved contradictions
  - stale decisions
  - source notes without citations
  - entity pages without recent observations

## Temporal Entity Memory

- Add stronger entity support for changing operational facts.
- Suggested frontmatter:
  - `entity_type`
  - `observed_at`
  - `valid_from`
  - `valid_until`
  - `source_confidence`
  - `supersedes`
  - `contradicts`

## Retrieval Router Contract

- Encode CHEAP/STANDARD/FULL retrieval routing directly in query commands.
- Context-gate before retrieving.
- Cap retrieval at three hops.
- Deduplicate between hops.
- Stop when new results overlap heavily with prior results.

## Progressive Disclosure Search

- Add a token-efficient three-layer search workflow:
  - `search`: compact result index with IDs and short snippets
  - `timeline`: chronological context around selected results
  - `get`: full note/observation details only for selected IDs
- Batch full-detail fetches by ID.
- Surface token cost estimates per layer when possible.
- Use this for session memory, saved observations, and wiki query history.

## Lifecycle Hook Capture

- Explore optional hooks for automatic candidate capture:
  - session start: load compact hot/context packet
  - user prompt submit: classify likely retrieval/save need
  - post tool use: capture important observations
  - stop/session end: compress session and offer/save durable outcomes
- Keep automatic capture as candidates, not direct approved memory.
- Add privacy controls:
  - `<private>...</private>` blocks are never stored
  - configurable path denylist
  - generated report/data denylist
  - PII-sensitive mode for client/customer projects

## Local Memory Viewer

- Add an optional local-only viewer for memory/wiki state.
- Show:
  - recent session summaries
  - candidate memories awaiting approval
  - approved/superseded memories
  - wiki lint status
  - retrieval hits with IDs
- Keep it disabled by default and loopback-only when enabled.

## Provider Configuration Precedence

- Define a consistent provider config precedence:
  1. shell environment
  2. local `.env`
  3. agent/client settings
  4. packet config
  5. built-in defaults
- Make request timeout, model, output language, and embedding endpoint configurable.
- For local models, expose longer request timeouts because compile-style wiki generation can exceed default SDK limits.

## Per-Concept Prompt Budgets

- When compiling or synthesizing pages from many sources, cap prompt content per concept.
- Allocate fair source shares when one concept has many contributing documents.
- Emit truncation warnings with the concept/page name and contributing sources.
- This keeps compile/query workflows predictable on smaller local models and large corpora.

## Committable Graph Artifacts

- For team onboarding, allow graph artifacts to be committed when intentionally generated.
- Suggested policy:
  - commit stable graph JSON and generated tours when useful for onboarding
  - ignore intermediate analyzer output
  - ignore diff overlays and local scratch
  - use Git LFS for large graph artifacts

## Multi-Platform Install Parity

- Keep the packet agent-neutral.
- Add explicit install notes for:
  - Codex
  - Claude Code
  - Antigravity
  - Cursor
  - Gemini CLI
  - Pi Agent
  - OpenCode/OpenClaw where applicable
- Prefer one shared source contract with thin per-agent adapters.
