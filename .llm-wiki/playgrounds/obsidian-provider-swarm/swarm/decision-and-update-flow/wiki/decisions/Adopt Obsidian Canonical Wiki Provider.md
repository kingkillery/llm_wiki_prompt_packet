---
type: decision
title: "Adopt Obsidian Canonical Wiki Provider"
created: 2026-05-06
updated: 2026-05-06
tags:
  - obsidian
  - decision
status: developing
related:
  - [[Canonical Wiki Provider]]
sources:
  - [[Spec: Obsidian Canonical Wiki Provider]]
decision_date: 2026-05-06
decision_status: active
---

Adopt the Obsidian canonical wiki provider for durable decision notes in this playground.

Rationale:
- The provider writes semantic wiki notes through the same save workflow used by agents.
- Decision notes should land under `wiki/decisions`.
- Index, log, and hot cache should be maintained by the save workflow.

Outcome:
- Treat this as the active decision for the playground validation run.

## Update 2026-05-06

Sources revisited: [[Spec: Obsidian Canonical Wiki Provider]]
Related: [[Direct File Wiki Provider]]
Update the existing durable decision after a later review.

Changes:
- Keep the Obsidian canonical wiki provider decision active.
- Clarify that the current implementation used direct-file transport as the local fallback.
- Confirm duplicate prevention by updating the prior decision note with the same title instead of creating a second note.

Outcome:
- The same decision remains active, with the later update appended.
