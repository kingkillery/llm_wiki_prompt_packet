# Harness Control Plane Retrieval Lifecycle (2026-04-25)

## Summary

The packet now has a v1 harness control-plane surface for state-of-the-art agentic bootstrap:

- compact default context via `llm-wiki-packet context`
- explicit broad evidence expansion via `llm-wiki-packet evidence`
- replayable run manifests via `llm-wiki-packet manifest`
- reducer packets and claim extraction via `llm-wiki-packet reduce`
- memory routing decisions via `llm-wiki-packet promote`
- run scoring via `llm-wiki-packet evaluate`
- benchmark-gated improvement proposals via `llm-wiki-packet improve`

## Design Rule

Default context stays lean. Hybrid/source-backed retrieval remains available through explicit evidence expansion when the task needs broader proof, stale-memory checks, graph/topology clues, or cited claims.

## Memory Routing

- Instructions and current task context stay in working memory.
- Run artifacts live under `.llm-wiki/skill-pipeline/runs/<run_id>/`.
- Durable facts are promoted to wiki only by explicit promotion.
- Reusable procedures become skill proposals before active-skill promotion.
- Preferences remain BRV-owned and require explicit curation.

## Verification

Targeted tests now cover:

- context bundle generation
- explicit evidence search
- run manifest/reduce/evaluate/improve lifecycle
- promotion decision-only default
- installer config parity for new runtime commands

Direct file I/O was used for this wiki update because Obsidian MCP availability was not confirmed in this session.
