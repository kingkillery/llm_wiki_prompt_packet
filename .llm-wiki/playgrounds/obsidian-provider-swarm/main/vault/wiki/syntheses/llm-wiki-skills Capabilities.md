---
type: synthesis
title: llm-wiki-skills Capabilities
created: '2026-05-06'
updated: '2026-05-06'
tags:
  - skills
  - llm-wiki-skills
status: developing
related: []
sources:
  - 'chat: llm-wiki-skills explanation'
---
# llm-wiki-skills Capabilities

`llm-wiki-skills` is the reusable skill lifecycle layer for the packet. It helps agents turn repeated work into reusable, reviewable shortcuts instead of letting useful process knowledge disappear into chat.

## What It Can Do

- Find relevant existing skills before an agent rediscovers a workflow.
- Capture lessons from long or repeated tasks into structured packets.
- Validate skills for usefulness, overlap, privacy risk, and quality.
- Merge or evolve existing skills instead of creating duplicates.
- Track which skills are currently strongest via the frontier.
- Record feedback after a skill is used.
- Retire stale or harmful skills cleanly.
- Keep skill artifacts organized under the local wiki/skill pipeline.

## Natural Language Requests

Users can ask:

- Do we already have a skill for this workflow?
- Turn what we just learned into a reusable skill.
- Review our existing skills and tell me what should be merged or retired.
- Improve the skill for debugging MCP startup failures.

## Operating Principle

Use `llm-wiki-skills` when the work should become reusable, reviewable, and cheaper next time, not just answered once.
