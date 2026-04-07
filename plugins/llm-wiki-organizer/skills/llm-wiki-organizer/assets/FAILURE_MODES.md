# Failure Modes

Known failure patterns for the llm-wiki-organizer skill. Each entry describes what goes wrong, how to detect it, and how to prevent or recover.

---

## FM-1: Duplicate page creation

**Symptom**: Two or more wiki pages cover the same entity, concept, or source with overlapping content.

**Root cause**: The skill created a new page without first searching for existing pages. Common when the existing page has a different filename than expected (e.g., `ai-agents.md` vs `llm-agents.md`).

**Detection**: Lint workflow finds pages with >60% content overlap. Manual review of index.md shows near-synonymous entries.

**Prevention**:
- Always search via pk-qmd and index.md before creating a page.
- Search by topic keywords, not just expected filenames.
- Check the CHECKLISTS.md preflight step for "search before create."

**Recovery**: Merge the duplicate into the older page. Update all backlinks. Delete the duplicate (with user confirmation). Update index.md and log.md.

---

## FM-2: Stale wiki summaries

**Symptom**: A wiki page cites claims that have been superseded by newer sources, but the page still shows the old information.

**Root cause**: A new source was ingested that contradicts or updates an earlier claim, but the affected wiki pages were not updated during that ingest run.

**Detection**: Lint workflow finds contradictions between pages or between a page and a newer source in `raw/`. The log.md shows an ingest that should have touched the page but didn't.

**Prevention**:
- During ingest, always check which existing wiki pages are materially affected by the new source.
- Use pk-qmd to search for pages containing claims related to the new source's key entities and concepts.
- Do not limit updates to the source-summary page alone.

**Recovery**: Re-read the newer source and the stale page. Update the page with current claims. Add a conflict note if the old claim had downstream dependents.

---

## FM-3: Wrong routing — brv used for broad search

**Symptom**: The skill queries brv for a broad codebase question and gets either no results or misleading results, wasting a turn.

**Root cause**: brv is a curated durable memory store, not a search engine. It only returns results for topics that were previously curated. Broad codebase searches belong to pk-qmd.

**Detection**: The `Stack/config used:` section shows brv as the first tool for a question about code, files, or repo structure.

**Prevention**:
- Follow the routing rules: pk-qmd first for repo-specific evidence, brv only for durable preferences and prior decisions.
- Check DECISION_RULES.md before routing.

**Recovery**: Re-run the query using pk-qmd. Note in the response that brv was not the right tool for this case.

---

## FM-4: Wrong routing — GitVizz used before pk-qmd

**Symptom**: GitVizz is invoked to find a file or symbol when the target area is completely unknown, returning broad or irrelevant graph results.

**Root cause**: GitVizz excels at mapping context around a known area, not at finding the area in the first place. When the target is unknown, pk-qmd's text search is the right starting point.

**Detection**: The `Stack/config used:` section shows GitVizz as the first tool, but the task description indicates the target area was not yet known.

**Prevention**:
- Use pk-qmd first to locate the relevant file, folder, or symbol.
- Use GitVizz second to map the surrounding context.
- See DECISION_RULES.md for the routing sequence.

**Recovery**: Follow up with pk-qmd to locate the target, then use GitVizz for context.

---

## FM-5: Missing index.md update

**Symptom**: A new wiki page exists but is not listed in `wiki/index.md`, making it undiscoverable.

**Root cause**: The skill created or renamed a page but skipped the index.md update step.

**Detection**: Glob for all files under `wiki/` and diff against entries in index.md. Any file not in the index is orphaned.

**Prevention**:
- The exit checklist in CHECKLISTS.md explicitly requires index.md review after any page creation, deletion, or rename.
- The eval check "index.md updated when needed" catches this.

**Recovery**: Add the missing entry to index.md. Append a correction entry to log.md.

---

## FM-6: Missing log.md update

**Symptom**: Substantive wiki work was done but `wiki/log.md` has no entry for it.

**Root cause**: The skill completed the wiki edits but skipped the log append step, usually because it returned the response before finishing the exit checklist.

**Detection**: Compare `Files changed:` in the response against the last log.md entry. If wiki pages were changed but log.md was not, this is a miss.

**Prevention**:
- The exit checklist requires a log.md append for any ingest, query-with-filing, lint, or schema change.
- Append to log.md as the final step, not a deferred step.

**Recovery**: Append a retroactive log entry noting the work and the gap.

---

## FM-7: Evidence-memory conflict silently resolved

**Symptom**: The wiki page shows updated information, but the response does not mention that brv memory disagreed with the current source evidence.

**Root cause**: The skill detected the conflict but resolved it silently (source wins) without surfacing the disagreement in the response.

**Detection**: The `Unresolved questions / conflicts:` section is empty despite brv and pk-qmd both being consulted on the same topic.

**Prevention**:
- Always surface conflicts in the response, even when the resolution is clear (source wins).
- Flag stale brv entries for curation.
- See eval check "Evidence-memory conflicts flagged."

**Recovery**: Amend the response or add a follow-up note in the wiki page and log.md describing the conflict and resolution.

---

## FM-8: Raw source files modified

**Symptom**: A file under `raw/` was edited or deleted.

**Root cause**: The skill treated a raw source as mutable, violating the immutability rule.

**Detection**: `git diff` shows changes under `raw/`. The `Files changed:` section lists a `raw/` path.

**Prevention**:
- Non-negotiable rule: never modify `raw/` unless the user explicitly asks.
- The tool directives and system prompt both state this rule.
- If the user asks to correct a raw source, confirm explicitly before proceeding.

**Recovery**: `git checkout` the raw file to restore the original. If the edit was intentional (user-confirmed), note it in log.md as an exception.

---

## FM-9: Response contract incomplete

**Symptom**: The response is missing one or more required fields (Task type, Stack/config used, Files read, Files changed, What changed, Unresolved questions / conflicts, Next best actions).

**Root cause**: The skill returned a narrative answer instead of following the output contract, or truncated the response before completing all fields.

**Detection**: Compare the response against the template in `output-contract.md`. Missing fields fail the eval.

**Prevention**:
- Use the output contract template for every operational turn.
- The exit checklist includes a contract completeness check.

**Recovery**: Append the missing fields to the response or issue a follow-up with the complete contract.

---

## FM-10: Startup sequence skipped

**Symptom**: The skill begins editing wiki pages without first reading AGENTS.md, config, index.md, or log.md.

**Root cause**: The skill jumped directly to the user's request without completing the required startup behavior.

**Detection**: The `Files read:` section does not include the startup files (AGENTS.md, wiki/index.md, etc.). The preflight checklist was not followed.

**Prevention**:
- The preflight checklist in CHECKLISTS.md must be completed before any edits.
- The system prompt lists 8 required startup steps.

**Recovery**: Stop, complete the startup sequence, then re-evaluate whether the edits already made are correct given the context that was missed.
