# Evaluation Criteria

Pass/fail checks for llm-wiki-organizer skill invocations. Use these to grade individual runs — manually, with a model-based grader, or in an automated eval harness.

Each check is binary: **pass** or **fail**. A run's overall grade is the fraction of applicable checks that pass.

---

## 1. Task classification

| Check | Pass condition |
|-------|---------------|
| Correct task type | The response labels the task as the correct type: `ingest`, `query`, `lint`, `schema`, or `other`. |
| Ambiguous tasks acknowledged | If the request spans multiple types (e.g., "ingest this and tell me what conflicts it creates"), both types are named. |

### How to grade

Compare the declared `Task type:` line against the user's request. If the user said "ingest," the task type must be `ingest`. If the request is ambiguous, both applicable types should appear.

---

## 2. Routing correctness

| Check | Pass condition |
|-------|---------------|
| pk-qmd used when needed | pk-qmd was invoked for repo-specific evidence retrieval, prompt/docs lookup, or broad search when target area was unknown. |
| pk-qmd not used unnecessarily | pk-qmd was skipped when the answer was already in open files or the task was pure reasoning/formatting. |
| GitVizz used when needed | GitVizz was invoked for repo topology, API surface, or dependency context after the relevant area was already located. |
| GitVizz not used as first search | GitVizz was not used as the initial broad search tool when the target area was unknown. |
| brv used appropriately | brv was consulted only for durable preferences, prior decisions, or workflow quirks — not for broad codebase questions. |
| brv skipped when unavailable | If brv has no connected provider, the run did not block waiting for brv. |
| Routing sequence correct | When both pk-qmd and GitVizz were used, pk-qmd ran first to locate the area, then GitVizz mapped context around it. |

### How to grade

Check the `Stack/config used:` section. Verify each tool was invoked for the right reason. Cross-reference against the routing rules in `system-prompt.md` and `tool-directives.md`.

---

## 3. No duplicate pages

| Check | Pass condition |
|-------|---------------|
| Search before create | The run searched the wiki (via index.md, pk-qmd, or glob) for existing related pages before creating any new page. |
| No duplicate created | No new page was created when an existing page already covered the same entity, concept, or source. |
| Merge over create | When overlapping content was found, the existing page was updated rather than a new page being created. |

### How to grade

List all files created in `Files changed:`. For each new file, verify that no pre-existing page in the wiki covers the same topic. Check the `Files read:` section to confirm a search was performed.

---

## 4. Index and log updates

| Check | Pass condition |
|-------|---------------|
| index.md updated when needed | `wiki/index.md` was updated whenever a new page was created, a page was deleted, or discoverability materially changed. |
| index.md not updated unnecessarily | `wiki/index.md` was left unchanged when no structural change occurred (e.g., minor edits to existing pages). |
| log.md updated for substantive work | `wiki/log.md` received an append entry for any ingest, query-with-filing, lint, or schema change. |
| log.md entry is well-formed | The log entry includes: date, task type, brief description, and files affected. |

### How to grade

Check whether `wiki/index.md` and `wiki/log.md` appear in `Files changed:`. If the run created or deleted pages, index.md must be there. If substantive work was done, log.md must be there.

---

## 5. Conflict surfacing

| Check | Pass condition |
|-------|---------------|
| Evidence-memory conflicts flagged | When pk-qmd evidence and brv memory disagreed, the conflict was explicitly stated in the response. |
| Source evidence wins | The response followed the rule: current source evidence beats memory for factual claims. |
| Stale memory identified | If brv returned outdated information, the response flagged it as stale and recommended updating. |
| Contradictions between pages noted | When wiki pages contained contradictory claims, the contradiction was surfaced in `Unresolved questions / conflicts`. |

### How to grade

Look for the `Unresolved questions / conflicts:` section. If the run involved both pk-qmd and brv, check whether any disagreements were noted. If contradictions exist between wiki pages that were read, they should appear here.

---

## 6. Response contract completeness

| Check | Pass condition |
|-------|---------------|
| All required fields present | The response includes: Task type, Stack/config used, Files read, Files changed, What changed, Unresolved questions / conflicts, Next best actions. |
| Fields are concrete | Each field contains specific file paths, tool names, or actionable items — not placeholders or vague language. |
| Response is compact | The response does not include unnecessary narration, preamble, or repeated information outside the contract fields. |

### How to grade

Verify all seven fields from `output-contract.md` are present. Check that each field has concrete content (file paths, not "various files"; specific tool names, not "the stack").

---

## 7. Definition of done

| Check | Pass condition |
|-------|---------------|
| Request addressed | The user's actual request was answered or fulfilled. |
| Wiki updates made or deferred | Relevant wiki pages were updated, or the response explicitly states why updates were deferred. |
| Uncertainties surfaced | Important unknowns, conflicts, or open questions were called out — not silently ignored. |
| Routing was evidence-based | Tool choices were justified by the task requirements, not by habit or default. |

### How to grade

This is the meta-check. A run passes definition-of-done only if all applicable checks above also pass.

---

## Grading summary template

```
Run ID: <identifier>
Task type: <declared type>
Applicable checks: <N>
Passed: <N>
Failed: <N>
Score: <passed/applicable as percentage>

Failed checks:
- <check name>: <brief reason>

Notes:
- <any context for borderline cases>
```

---

## Using these evals

**Manual review**: Walk through each section after a skill run. Mark pass/fail.

**Model-based grader**: Feed the user request, the skill's full response, and this file to a grader model. Ask it to evaluate each check and return the summary template.

**Automated harness**: For each test case in `EXAMPLES.md`, run the skill, capture the response, and grade programmatically against the applicable checks. Flag regressions when a previously-passing check fails.

**Continuous improvement**: When a new failure mode is discovered (see `FAILURE_MODES.md`), add a corresponding eval check here. When a process improvement is approved (see `PROCESS_IMPROVEMENTS.md`), verify it with a new eval case.
