# Obsidian Provider Decision Save/Update Test

Date: 2026-05-06

Workspace:

```text
.llm-wiki/playgrounds/obsidian-provider-swarm/swarm/decision-and-update-flow
```

## Commands

Initial durable decision save:

```powershell
python support\scripts\llm_wiki_save.py --workspace .llm-wiki\playgrounds\obsidian-provider-swarm\swarm\decision-and-update-flow --title "Adopt Obsidian Canonical Wiki Provider" --type decision --body-file .llm-wiki\playgrounds\obsidian-provider-swarm\swarm\decision-and-update-flow\inputs\decision-initial.md --source "[[Spec: Obsidian Canonical Wiki Provider]]" --related "[[Canonical Wiki Provider]]" --tag obsidian --tag decision --mode create-or-update
```

Output:

```text
created: wiki/decisions/Adopt Obsidian Canonical Wiki Provider.md (direct-file)
```

Later same-decision update:

```powershell
python support\scripts\llm_wiki_save.py --workspace .llm-wiki\playgrounds\obsidian-provider-swarm\swarm\decision-and-update-flow --title "Adopt Obsidian Canonical Wiki Provider" --type decision --body-file .llm-wiki\playgrounds\obsidian-provider-swarm\swarm\decision-and-update-flow\inputs\decision-update.md --source "[[Spec: Obsidian Canonical Wiki Provider]]" --related "[[Direct File Wiki Provider]]" --tag obsidian --tag decision --mode create-or-update
```

Output:

```text
updated: wiki/decisions/Adopt Obsidian Canonical Wiki Provider.md (direct-file)
```

Duplicate count check:

```powershell
(Get-ChildItem -File .llm-wiki\playgrounds\obsidian-provider-swarm\swarm\decision-and-update-flow\wiki\decisions\*.md).Count
```

Output:

```text
1
```

## Files Created/Updated

- `.llm-wiki/config.json` - workspace-local wiki provider config with `wiki_layer.vault_path` set to `.`, Obsidian provider metadata, and direct-file fallback enabled.
- `inputs/decision-initial.md` - initial durable decision body.
- `inputs/decision-update.md` - later update body.
- `wiki/decisions/Adopt Obsidian Canonical Wiki Provider.md` - created on first save, updated on second save.
- `wiki/index.md` - created and populated with one Decisions entry.
- `wiki/log.md` - created and prepended with save entries.
- `wiki/hot.md` - created/updated as the recent context cache.
- `result.md` - this report.

## Duplicate Behavior

The second save used the same title and type with `--mode create-or-update`. The save script found the existing decision by normalized title/frontmatter title and updated it instead of creating a duplicate.

Observed behavior:

- First command action: `created`
- Second command action: `updated`
- Decision markdown files after both saves: `1`
- The original note now includes an appended `## Update 2026-05-06` section with the later review details.

## Index Observations

`wiki/index.md` contains one decision entry:

```markdown
# Wiki Index

## Decisions
- [[Adopt Obsidian Canonical Wiki Provider]]: decision (status: developing)
```

No duplicate index line was added during the update.

## Log Observations

`wiki/log.md` contains two entries for the same decision path, newest first:

- `Action: updated`
- `Action: created`

Both entries point to:

```text
wiki/decisions/Adopt Obsidian Canonical Wiki Provider.md
```

## Hot Cache Observations

`wiki/hot.md` was overwritten with the latest save context. After the update it reports:

```markdown
- Updated: [[Adopt Obsidian Canonical Wiki Provider]]
```

The hot cache reflects only the most recent save action, which is consistent with the current implementation of `update_hot()`.

## Transport Observation

The configured provider is Obsidian in the workspace-local config, but this test used the implemented direct-file provider path:

```text
(direct-file)
```

That is expected for the current script because MCP/REST adapters are still extension points and direct-file fallback is enabled in the local config.
