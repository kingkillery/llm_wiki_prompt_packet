# Memory Layering

The stack uses five distinct memory layers. Each has a specific store, retrieval path, and write trigger.

## Layers

| Layer | Store | Write trigger | Read path |
|---|---|---|---|
| **Working** | Active prompt context, `AGENTS.md`, `CLAUDE.md`, open files | Always present; no explicit write | Read at session start |
| **Episodic** | `.llm-wiki/skill-pipeline/briefs/`, `packets/`, `failures/` | After any task with real exploration cost | `pk-qmd` search or direct path lookup |
| **Semantic** | `wiki/concepts/`, `wiki/syntheses/`, `wiki/entities/`, etc. | After validation; when a fact should survive the current session | `pk-qmd` semantic/lex search |
| **Procedural** | `wiki/skills/active/` + `skills-registry.json` | After skill pipeline validation (`route_decision: complete`) | `skill_lookup` MCP tool or `pk-qmd` |
| **Preference** | `brv` context tree | Stable user or workflow preference worth recalling across projects | `brv query` |

## Promotion flow

```
raw task output
    → reducer packet (episodic)
        → validated fact → wiki page (semantic)
        → validated shortcut → active skill (procedural)
        → user/workflow preference → brv curate (preference)
```

Never write directly to semantic or procedural memory without a validation step. Episodic artifacts are the staging area.

## Conflicts

When `brv` and `wiki/` disagree, trust current source evidence (`pk-qmd`). Update or retire the stale layer rather than silently working around it.

When `brv` has no connected provider, store preference-class knowledge in `wiki/concepts/` temporarily with a `<!-- brv-pending -->` comment so it can be migrated once a provider is connected.

## References

- `LLM_WIKI_MEMORY.md` — routing rules and wiki/brv routing table
- `SKILL_CREATION_AT_EXPERT_LEVEL.md` — skill promotion pipeline details
- `SYSTEM_CONTRACT.md` — canonical layer-to-store mapping
