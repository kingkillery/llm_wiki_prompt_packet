# Retrieval Spine Hardening (2026-04-25)

## Summary

The packet retrieval spine now treats `llm-wiki-packet context` and `llm-wiki-packet evidence` as real integrated retrieval surfaces instead of only structured local fallbacks.

## Changes

- `pk-qmd` command resolution prefers managed Windows-safe wrappers and `dist/cli/qmd.js` through Node, and rejects npm shell shims that route through `/bin/sh` on Windows.
- Source retrieval tries JSON-producing `pk-qmd search` and `query` forms first, then parses stable text output into standard evidence records before falling back to local lexical search.
- External retrieval subprocesses decode as UTF-8 with replacement so Windows codepage mismatches do not break smoke runs on Unicode output.
- BRV preference retrieval probes connected providers before querying, uses a longer default query timeout, and parses `data.result` markdown from current BRV JSON responses.
- GitVizz graph retrieval posts to the task-shaped context search endpoint when a repo id is known; auth or request-shape failures produce degraded graph records plus config hints.
- Hugging Face model names are recorded as optional planner defaults only. They are disabled by default and do not become bootstrap dependencies.
- Manifest and evaluation artifacts can store retrieval planes used, per-plane statuses, degraded/error summaries, and whether compact default context was sufficient.

## Operating Rule

Default context remains lean. Deep source, preference, graph, and optional embedding/reranking paths run only when the agent asks for deep context or explicit evidence expansion.
