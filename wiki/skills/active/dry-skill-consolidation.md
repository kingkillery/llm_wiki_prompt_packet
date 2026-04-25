---
skill_id: skill-dry-skill-consolidation
title: DRY skill consolidation
kind: prompt
memory_scope: procedural
memory_strategy: hierarchical
update_strategy: merge_append
confidence: high
applies_to:
  - "*/skills/*/SKILL.md"
  - "*/skills/*/SKILLS.md"
  - "skill consolidation audit"
created_at: 2026-04-25
validation_status: validated
validation_score: 8
pii_review: passed
provenance_refs:
  - "C:\\Users\\prest\\.codex\\skills\\dry-skill-consolidation\\SKILL.md"
---

# DRY skill consolidation

## Trigger

Use when a user asks to audit, deduplicate, merge, or rewrite a directory of `SKILL.md` or `SKILLS.md` files while preserving hard requirements.

## Preconditions

- The target scope contains skill files or the user provides skill text.
- The task is about reducing top-level skill choice around user intent.
- Hard safety, tool, permission, output, citation, and validation requirements must be preserved.

## Fast Path

Use the installed Codex skill at:

`C:\Users\prest\.codex\skills\dry-skill-consolidation`

Core flow:

1. Inventory all skill files in scope.
2. Extract primary user intent and hard requirements from each file.
3. Score potential merges with the 0-10 consolidation rubric.
4. Merge only when the combined skill is easier to choose and no weaker in safety or specificity.
5. Move branch-specific details into references.
6. Return the required `Skill Consolidation Audit` structure.

## Failure Modes

- **Over-broad merge**: keep skills separate when user intent, safety boundaries, permission risk, runtime requirements, or validation logic differ materially.
- **Hidden hard rule**: safety, permission, tool, and validation requirements that prevent wrong tool use must stay top-level.
- **Template drift**: use `references/audit-contract.md` in the installed skill before drafting the final audit.

## Durable Facts

- The installable skill is named `dry-skill-consolidation`.
- The detailed audit output contract lives in `references/audit-contract.md` to keep `SKILL.md` concise.
- Validation passed with the system `quick_validate.py` script on 2026-04-25.

## Skip Steps Estimate

Saves repeated reconstruction of merge criteria, scoring, progressive disclosure structure, and audit output format.
