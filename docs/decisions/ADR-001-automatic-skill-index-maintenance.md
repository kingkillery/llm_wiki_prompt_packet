# ADR-001: Automatically maintain the skill suggestion index

## Status
Accepted

## Date
2026-04-22

## Context
The packet now relies on a skill suggestion index (`.llm-wiki/skill-index.json`) for proactive procedural-memory retrieval. That index folds together:

- active skills from `wiki/skills/active/`
- retired-skill penalties from `wiki/skills/retired/`
- negative feedback from `.llm-wiki/skill-pipeline/feedback.jsonl`
- retrieval settings from `.llm-wiki/config.json`

A manual rebuild step is acceptable for packet authors, but it is the wrong UX for downstream users. Most users of the installed packet should not need to understand how the index is built, when it becomes stale, or which artifacts influence ranking.

The old model had two problems:

1. setup could finish successfully while leaving the suggestion index absent
2. feedback and retired-skill changes could silently leave the index stale until someone manually rebuilt it

## Decision
Treat the skill suggestion index as a **managed derived artifact**, not a user-maintained file.

We will:

1. build or refresh the skill index during setup and health-check flows
2. lazily rebuild it at runtime when interactive wrapped agent launches or the dashboard access a stale or missing index
3. detect staleness from the mtimes of:
   - `.llm-wiki/config.json`
   - `wiki/skills/active/*.md`
   - `wiki/skills/retired/*.md`
   - `.llm-wiki/skill-pipeline/feedback.jsonl`
4. keep the manual fallback command for debugging:
   - `python scripts/build_skill_index.py --workspace <repo>`

## Alternatives Considered

### Keep manual rebuilds only
- Pros: simplest implementation
- Cons: users get missing suggestions, stale ranking, and broken dashboard expectations unless they know internal maintenance steps
- Rejected: violates the packet goal of hiding maintenance complexity behind a stable harness

### Rebuild after every write event only
- Pros: more immediate than manual rebuilds
- Cons: still misses cases like config edits, copied-in skills, or direct file changes outside the formal pipeline
- Rejected: too brittle for a markdown-first local system

### Fully in-memory indexing only
- Pros: no persisted artifact to manage
- Cons: slower cold starts, less inspectable state, and harder debugging for retrieval quality issues
- Rejected: conflicts with the packet's local-first, inspectable-artifact philosophy

## Consequences

### Positive
- setup leaves the workspace in a suggestion-ready state
- end users do not need to learn index maintenance internals
- runtime ranking stays aligned with retired-skill and feedback updates
- the dashboard and wrapped agent sessions surface current procedural memory more reliably

### Negative
- setup/check now perform extra work
- runtime may pay a small rebuild cost when the index is stale
- staleness detection is mtime-based, which is pragmatic rather than semantically perfect

## Notes
This decision deliberately keeps the index human-debuggable while removing the expectation that users manage it manually. That matches the packet's broader local-first principle: derived artifacts may be inspectable, but their upkeep should be automatic whenever possible.
