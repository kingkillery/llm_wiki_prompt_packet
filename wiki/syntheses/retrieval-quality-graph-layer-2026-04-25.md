# Retrieval Quality And Graph Layer (2026-04-25)

## Summary

The next retrieval layer tightened graph access, result quality signals, context budgets, and run-manifest linkage.

## Changes

- GitVizz retrieval now prefers a configured `gitvizz.repo_id` and supports auth through `gitvizz.authorization_env` or `gitvizz.auth_token_env`.
- GitVizz health checks probe the task-shaped context-search endpoint and report whether graph search is usable, auth-required, degraded, or missing a repo id.
- Retrieval records now include matched query terms, confidence reasons, and source-precedence reasons so agents can explain why evidence was ranked.
- Context output applies per-section budgets so instructions, skills, evidence, recent lessons, preferences, and graph hints cannot crowd each other out.
- `context` and `evidence` accept `--run-id` and append retrieval-plane status metadata directly to the run manifest.

## Operating Rule

Use default context for startup. Use explicit evidence or graph mode for broad search, and attach `--run-id` during long-running harness work so retrieval health is auditable during evaluation.
