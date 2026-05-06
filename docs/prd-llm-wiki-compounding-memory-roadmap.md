# PRD: LLM Wiki Compounding Memory Roadmap

## Problem Statement

Users want `llm_wiki_prompt_packet` to behave like a durable, compounding wiki operating system for agents, not just a collection of prompts, scripts, and retrieval helpers. Today the packet can install wiki folders, save structured Obsidian-backed notes, run retrieval, and maintain skill/memory artifacts, but the experience is still uneven:

- high-value answers can be saved, but the save policy is not yet backed by conflict detection, saved-query pages, or promotion gates
- wiki health checks exist mostly as prompt behavior, not as a concrete lint/status system
- `wiki/hot.md` exists, but there is no first-class `wiki/overview.md` or session-end refresh discipline
- graph support is oriented toward repo topology rather than a navigable wiki knowledge graph
- retrieval returns useful context, but it does not yet expose a token-efficient progressive search workflow
- raw source ingestion is not yet compiler-like: source hashes, compile state, incremental updates, and per-concept prompt budgets are not formalized

The result is that durable knowledge can still scatter across chat history, wiki pages, logs, skill artifacts, and project-specific notes. Users need a clearer system that captures, compiles, validates, retrieves, and visualizes durable knowledge without making the vault noisy or fragile.

## Solution

Build a staged "compounding memory" upgrade for `llm_wiki_prompt_packet`.

From the user's perspective, the packet should:

- keep a living overview of what a repo or vault is about
- save durable answers, decisions, research, and source conflict resolutions into the right note types
- detect likely conflicts before saving or compiling new knowledge
- compile raw sources into interlinked wiki pages incrementally
- expose a clear wiki status/lint report
- let agents retrieve in layers: compact result index first, timeline/context second, full details last
- generate guided tours and optional graph artifacts for onboarding and handoff
- maintain privacy controls for automatic capture and session summaries
- remain agent-neutral across Codex, Claude Code, Antigravity, Cursor, Gemini CLI, Pi Agent, and related runtimes

The work should extend the existing packet architecture. It should not replace the Obsidian provider, `pk-qmd`, BRV, GitVizz integration, or the current installer model.

## User Stories

1. As a user, I want the packet to maintain a living overview of my repo or vault, so that future agents can understand the workspace quickly.
2. As a user, I want durable research answers saved automatically or offered for save, so that useful findings do not disappear into chat history.
3. As a user, I want saved answers to cite their source notes, so that I can audit claims later.
4. As a user, I want high-value queries saved under a dedicated query note type, so that repeated questions do not rediscover the same answer.
5. As a user, I want query notes to be promotable into concepts, syntheses, or decisions, so that the wiki improves over time.
6. As a user, I want the save workflow to search existing notes before writing, so that duplicate notes are avoided.
7. As a user, I want the save workflow to flag conflicting claims, so that stale or contradictory knowledge is not silently accepted.
8. As a user, I want decisions to support `supersedes` and `contradicts` metadata, so that decision history remains understandable.
9. As a user, I want entity pages to track observation time and validity windows, so that changing operational facts are represented accurately.
10. As a user, I want the packet to distinguish source-backed facts from guesses, so that future agents know what to trust.
11. As a user, I want an explicit wiki lint command, so that orphans, broken links, stale decisions, missing metadata, and contradictions are visible.
12. As a user, I want a wiki status command, so that I can see source counts, page counts, pending compiles, stale pages, and lint health.
13. As a user, I want raw sources compiled incrementally, so that unchanged sources are not reprocessed.
14. As a user, I want source hashes and compile state tracked, so that the packet can explain what changed since the last compile.
15. As a user, I want per-concept prompt budgets, so that large source collections do not overload a model context window.
16. As a user using a local model, I want configurable request timeouts, so that long compile operations do not fail prematurely.
17. As a user working in another language, I want output language configuration, so that generated wiki pages match my preferred language.
18. As an agent, I want a compact search result index before full note content, so that I can avoid wasting tokens.
19. As an agent, I want a timeline/context step around selected search results, so that I can understand when and why a note was created.
20. As an agent, I want full note content only for selected IDs, so that retrieval remains cheap and focused.
21. As an agent, I want retrieval routing to choose CHEAP, STANDARD, or FULL modes, so that I do not over-retrieve.
22. As an agent, I want retrieval to stop when new results heavily overlap old results, so that I avoid redundant hops.
23. As an agent, I want retrieval to cap at three hops, so that interactive sessions remain bounded.
24. As an agent, I want saved query answers included in later retrieval, so that the wiki compounds through usage.
25. As a maintainer, I want a graph artifact for the wiki, so that note relationships are testable and inspectable.
26. As a maintainer, I want graph edges labeled as extracted, inferred, or ambiguous, so that inferred structure is not confused with explicit links.
27. As a maintainer, I want graph artifacts cached by source hash, so that graph builds are incremental.
28. As a teammate, I want guided tours through the wiki or repo, so that onboarding starts with the right pages in the right order.
29. As a teammate, I want committed graph and tour artifacts when appropriate, so that I can inspect project structure without rerunning the pipeline.
30. As a developer, I want diff impact analysis, so that I can see which wiki pages, decisions, skills, and entities may be stale before committing.
31. As a developer, I want intermediate graph outputs ignored by default, so that local scratch artifacts do not pollute git.
32. As a user, I want optional lifecycle capture at session start, user prompt, post-tool-use, stop, and session end, so that important observations become candidates.
33. As a user, I want automatic capture to create candidates, not approved memory, so that noisy or sensitive observations do not enter the durable wiki unchecked.
34. As a user, I want `<private>...</private>` blocks excluded from memory capture, so that sensitive instructions stay out of persistent storage.
35. As a user, I want configurable deny lists for paths and generated artifacts, so that reports, datasets, screenshots, and PII-heavy files are not captured accidentally.
36. As a user in a client/customer project, I want a PII-sensitive mode, so that the packet is conservative about storing operational data.
37. As a user, I want an optional local-only memory viewer, so that I can inspect candidates, approved memories, lint health, and retrieval hits.
38. As a user, I want the viewer disabled by default, so that the base packet remains lightweight.
39. As a maintainer, I want provider configuration precedence documented, so that env vars, `.env`, agent settings, packet config, and defaults resolve predictably.
40. As a maintainer, I want platform-specific install parity, so that each agent runtime uses the same source contract with thin adapters.
41. As a maintainer, I want Obsidian symlink mode documented as advanced and opt-in, so that direct vault writes stay the safe default.
42. As a maintainer, I want tests around external behavior, so that lint, save, status, retrieval, and compile behavior do not regress.
43. As a maintainer, I want implementation split into deep modules with narrow interfaces, so that future transports and graph/rendering layers can evolve independently.
44. As a user, I want all new features to be optional unless they affect core save/query correctness, so that existing installs remain stable.
45. As a user, I want the packet to keep working without Obsidian Desktop, so that filesystem-backed and MCP-backed operation remain viable.

## Implementation Decisions

- Build this as a phased roadmap rather than one monolithic feature.
- Keep Obsidian as the canonical human wiki layer when configured, with direct file fallback only against an explicit vault path.
- Add `overview` and `queries` as first-class wiki concepts alongside existing index, log, hot cache, source, concept, synthesis, decision, entity, question, and session notes.
- Add a wiki compiler module that owns source normalization, source hashing, compile state, incremental page generation, saved query integration, and structured compile/status output.
- Add a wiki lint module that owns orphan detection, broken link detection, required frontmatter validation, duplicate detection, unresolved contradiction checks, stale decision checks, and source citation checks.
- Add a wiki graph module that owns wikilink extraction, category extraction, optional inferred edges, graph JSON output, graph HTML output, graph caching, and guided-tour source data.
- Add a retrieval router module that owns context gating, CHEAP/STANDARD/FULL tiering, result deduplication, hop limits, overlap stops, and progressive disclosure result IDs.
- Add a memory capture module that owns lifecycle event normalization, privacy filters, candidate creation, and handoff into the existing memory ledger.
- Add a provider settings module that owns configuration precedence for model, timeout, language, embedding endpoint, and provider-specific settings.
- Keep visualization and local viewer features optional and loopback-only.
- Treat graph artifacts and guided tours as committable only when intentionally generated; ignore intermediate and scratch artifacts by default.
- Do not directly copy AGPL-licensed code or implementation details from `claude-mem`; only borrow high-level architectural patterns.
- Do not make remote services mandatory for core save/query/lint/status behavior.

## Testing Decisions

- Tests should assert external behavior rather than implementation details.
- Save workflow tests should verify duplicate handling, conflict metadata, index/log/hot/overview updates, query-page creation, and explicit-vault safeguards.
- Compiler tests should verify source hash state, incremental no-op behavior, changed-source recompilation, structured warnings, prompt budget enforcement, and saved query inclusion.
- Lint tests should verify orphan detection, broken wikilinks, missing frontmatter, duplicate notes, unresolved contradictions, stale decisions, and source notes without citations.
- Retrieval router tests should verify context gate skips, tier selection, hop caps, deduplication, overlap stopping, and progressive disclosure output shape.
- Graph tests should verify explicit wikilink extraction, edge provenance labels, graph cache invalidation, and stable JSON output.
- Memory capture tests should verify privacy filters, deny lists, candidate-only persistence, and session-end summary behavior.
- Provider config tests should verify precedence across environment, local `.env`, agent settings, packet config, and defaults.
- Existing tests around Obsidian provider, installer config, and memory runtime should be extended rather than duplicated.

## Out of Scope

- Replacing `pk-qmd`, BRV, GitVizz, or the existing Obsidian provider.
- Building a full Obsidian plugin.
- Requiring Obsidian Desktop for local filesystem operation.
- Building a hosted multi-user service.
- Automatically committing generated graph/wiki artifacts.
- Capturing raw screenshots, portal exports, customer datasets, or PII-heavy reports without explicit opt-in.
- Direct code reuse from incompatible-license projects.
- Full semantic graph inference in the first milestone.
- Full multi-format document conversion in the first milestone.

## Further Notes

The roadmap should prioritize correctness and memory hygiene before visual polish. The first useful release should make the wiki safer and more durable: overview, saved query pages, lint/status, conflict-aware saves, and retrieval routing. Graphs, guided tours, lifecycle hooks, and local viewers should follow once the core wiki state is reliable.

This PRD is derived from `possible-improvements.md`, which collected patterns from adjacent projects including Obsidian wiki companions, LLM wiki compilers, code/knowledge graph tools, and session-memory systems.
