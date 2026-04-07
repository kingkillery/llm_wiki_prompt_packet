# Process Improvements

Append-only log of approved changes to the llm-wiki-organizer skill's behavior. Each entry records what changed, why, and when it was approved.

This file exists so the skill improves deliberately rather than improvising new rules on every run. Only add entries here when a change has been validated — not for speculative ideas.

---

## How to use this file

**When to add an entry**: After a failure mode is observed, diagnosed, and a fix is validated (either by the user confirming the fix or by an eval run showing improvement).

**Entry format**:

```
### PI-<number>: <short title>
- **Date**: <YYYY-MM-DD>
- **Triggered by**: <failure mode ID from FAILURE_MODES.md, eval failure, or user feedback>
- **Change**: <what behavior changed>
- **Rationale**: <why this is an improvement>
- **Validated by**: <how we confirmed the change works — user confirmation, eval pass, or lint run>
- **Files affected**: <which skill pack files were updated>
```

**What not to add**: Speculative improvements, one-off workarounds, or changes that haven't been tested. If you have an idea but haven't validated it, note it as a candidate in the section below.

---

## Approved improvements

### PI-1: Search by keywords, not just filenames

- **Date**: 2026-04-07
- **Triggered by**: FM-1 (duplicate page creation)
- **Change**: Preflight search step now explicitly requires searching by topic keywords, not just expected filenames.
- **Rationale**: Duplicate pages were created because the skill searched for `ai-agents.md` but the existing page was named `llm-agents.md`. Keyword search catches these.
- **Validated by**: Added to preflight checklist and EXAMPLES.md (Example 3 demonstrates the merge-over-create pattern).
- **Files affected**: CHECKLISTS.md, EXAMPLES.md

### PI-2: Always surface evidence-memory conflicts

- **Date**: 2026-04-07
- **Triggered by**: FM-7 (silent conflict resolution)
- **Change**: Even when the resolution is clear (source wins), the response must explicitly flag the disagreement and recommend brv curation.
- **Rationale**: Silent resolution hides stale memory from the user and from future runs. Surfacing it enables cleanup.
- **Validated by**: Added eval check "Evidence-memory conflicts flagged" and demonstrated in EXAMPLES.md Example 4.
- **Files affected**: EVALS.md, EXAMPLES.md, FAILURE_MODES.md

### PI-3: Append log.md as the final step

- **Date**: 2026-04-07
- **Triggered by**: FM-6 (missing log.md update)
- **Change**: log.md append is now the last step in the exit checklist, not a deferred step that can be forgotten.
- **Rationale**: When log.md was a "remember to do this" step, it was sometimes skipped when the skill returned early.
- **Validated by**: Moved to final position in exit checklist.
- **Files affected**: CHECKLISTS.md

---

## Candidate improvements (not yet validated)

_Add ideas here. Move them to "Approved improvements" after validation._

- **Candidate**: Add a "confidence" field to the response contract indicating how well-grounded the answer is (fully cited, partially inferred, speculative).
- **Candidate**: Auto-generate a lint report after every ingest to catch immediate issues introduced by the new source.
- **Candidate**: Track which brv entries have been flagged as stale and auto-suggest a curation batch when the count exceeds a threshold.
