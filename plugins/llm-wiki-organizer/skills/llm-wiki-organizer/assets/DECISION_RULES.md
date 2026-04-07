# Decision Rules

Quick-reference tables for routing and task decisions. These condense the rules from the system prompt and tool directives into scannable lookup format.

---

## Tool routing decision table

Use this table to pick the right tool for the current need. Read top to bottom; use the **first matching row**.

| Condition | First tool | Second tool | Rationale |
|-----------|-----------|-------------|-----------|
| Target file/folder/symbol is unknown | `pk-qmd` | `GitVizz` (after pk-qmd locates the area) | pk-qmd does broad text search; GitVizz maps context around a known area. |
| Target area is known, need surrounding context | `GitVizz` | — | GitVizz excels at dependency graphs, API surface, and route relationships. |
| Need exact text, quote, or prompt content | `pk-qmd` | — | pk-qmd is the text retrieval tool. |
| Need repo topology, routes, or API surface | `GitVizz` | — | GitVizz indexes repo structure and serves graph views. |
| Need a prior decision, preference, or workflow quirk | `brv` | — | brv stores curated durable memory. |
| Answer is already in open files or prompt | None | — | Do not invoke tools unnecessarily. |
| Task is pure reasoning, formatting, or rewriting | None | — | No retrieval needed. |
| brv has no connected provider | Skip `brv` | `pk-qmd` or source files | Do not block on unavailable brv. Fall back to source evidence. |

---

## Tool routing sequence diagram

```
User request
    |
    v
Is the answer already in open files?
    |-- Yes --> Answer directly. No tool needed.
    |-- No
        |
        v
    Is the target area known?
        |-- No --> pk-qmd (broad search)
        |           |
        |           v
        |       Found? --> GitVizz (map context)
        |
        |-- Yes
            |
            v
        What do you need?
            |-- Text/evidence --> pk-qmd
            |-- Topology/API/deps --> GitVizz
            |-- Prior decision/preference --> brv (if available)
```

---

## Task classification rules

| User says | Task type | Key signal |
|-----------|-----------|------------|
| "ingest," "process," "add this source" | `ingest` | New source material entering the wiki. |
| "what," "how," "why," "explain," "find" | `query` | Question to be answered from the wiki or stack. |
| "lint," "audit," "check," "health," "duplicates" | `lint` | Structural or quality review of existing wiki. |
| "schema," "convention," "rename pattern," "restructure" | `schema` | Change to wiki structure, naming, or conventions. |
| Anything else | `other` | Does not fit the four primary types. |
| Spans multiple types | Name all applicable types | E.g., "ingest this and flag conflicts" = `ingest` + `lint`. |

---

## Evidence hierarchy

When sources disagree, resolve using this priority order:

1. **Current source evidence** (files in `raw/`, current code, live config)
2. **Wiki pages** (mutable, may be stale)
3. **brv durable memory** (curated, but may be outdated)
4. **Inferred relationships** (GitVizz graph connections)

Always flag the conflict in the response, even when the resolution is clear.

---

## Follow-through decision rules

| Action | Proceed without asking? | Ask first? |
|--------|------------------------|------------|
| Read files | Yes | — |
| Run pk-qmd | Yes | — |
| Consult brv | Yes | — |
| Update a few wiki pages | Yes | — |
| Update index.md | Yes | — |
| Append to log.md | Yes | — |
| Delete a page | — | Yes |
| Large rename or restructure | — | Yes |
| Change schema conventions | — | Yes |
| Edit files outside wiki layer | — | Yes |
| Auth or login flows | — | Yes |

---

## When to file a query answer back into the wiki

| Condition | File it? |
|-----------|----------|
| Answer synthesizes multiple sources into durable insight | Yes |
| Answer resolves a recurring question | Yes |
| Answer is code-specific and better read from source | No |
| User explicitly says "chat-only" or "don't file" | No |
| Answer is transient (e.g., "what's the current git status") | No |

---

## When to write to brv

| Condition | Write? |
|-----------|--------|
| Learned item is reusable across sessions | Yes |
| Learned item is stable (not likely to change soon) | Yes |
| Learned item was costly to discover | Yes |
| Learned item is already obvious from source docs | No |
| Item is raw command output or temporary status | No |
| Item is speculative or unverified | No |
