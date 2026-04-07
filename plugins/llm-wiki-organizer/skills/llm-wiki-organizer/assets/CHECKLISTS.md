# Checklists

Repeatable preflight and exit routines for the llm-wiki-organizer skill. Run the preflight before any edits. Run the exit checklist before returning the response.

---

## Preflight checklist (before edits)

Complete every applicable step in order. Do not skip steps.

- [ ] Read `AGENTS.md`
- [ ] Read `LLM_WIKI_MEMORY.md` (if present)
- [ ] Read `.llm-wiki/config.json` (if present)
- [ ] Verify stack readiness: pk-qmd, brv, GitVizz
  - If any component is missing or inactive, run `scripts/setup_llm_wiki_memory.ps1` or `.sh`
  - If brv has no connected provider, note it and proceed without brv
- [ ] Read `wiki/index.md`
- [ ] Read recent entries from `wiki/log.md`
- [ ] Classify the task: `ingest`, `query`, `lint`, `schema`, or `other`
- [ ] Search the wiki for existing pages related to the task
  - Search by topic keywords, not just expected filenames
  - Check index.md entries and use pk-qmd for broader search
- [ ] Identify the correct routing: pk-qmd, GitVizz, brv, or none
  - Refer to `DECISION_RULES.md` if uncertain

---

## Exit checklist (before returning the response)

Complete every applicable step. Mark N/A for steps that do not apply to this task type.

### Wiki integrity

- [ ] No duplicate pages created (searched before creating)
- [ ] No raw source files modified (unless user explicitly asked)
- [ ] All new pages are linked from at least one other page
- [ ] `wiki/index.md` updated if pages were created, deleted, or renamed
- [ ] `wiki/log.md` appended if substantive work was done

### Conflict handling

- [ ] Evidence-memory conflicts explicitly flagged (if pk-qmd and brv were both consulted)
- [ ] Contradictions between wiki pages surfaced in response
- [ ] Source evidence given priority over memory for factual claims
- [ ] Stale brv entries flagged for curation

### Response contract

- [ ] Task type declared
- [ ] Stack/config used listed with specific tool names and search terms
- [ ] Files read listed with specific paths
- [ ] Files changed listed with specific paths
- [ ] What changed described in concrete bullets
- [ ] Unresolved questions / conflicts listed (or explicitly "none")
- [ ] Next best actions listed (1-3 concrete steps)

### Definition of done

- [ ] The user's request was addressed
- [ ] Relevant wiki updates were made or explicitly deferred with reason
- [ ] Important uncertainties or conflicts were surfaced
- [ ] Routing decisions were evidence-based, not habitual

---

## Task-specific additions

### Ingest tasks

Add these checks to the exit checklist:

- [ ] Source-summary page created or updated
- [ ] Materially affected entity, concept, synthesis, comparison, or timeline pages updated
- [ ] New entities and concepts extracted — not just the top-level topic
- [ ] Open questions and uncertainties from the source recorded

### Query tasks

Add these checks to the exit checklist:

- [ ] Answer is grounded in specific sources (not vague references)
- [ ] If the answer creates durable value, it was filed into the wiki
- [ ] If the answer is code-specific or transient, it was not unnecessarily filed

### Lint tasks

Add these checks to the exit checklist:

- [ ] Safe fixes applied directly
- [ ] Higher-judgment recommendations listed separately
- [ ] Deletion of pages confirmed with user before executing
- [ ] Thin or stub pages flagged for expansion

### Schema tasks

Add these checks to the exit checklist:

- [ ] User confirmed the schema change before execution
- [ ] All affected pages updated to match new conventions
- [ ] index.md updated to reflect structural changes
- [ ] log.md entry describes the schema change and rationale
