---
skill_id: skill-submodule-commit-and-parent-pointer-bump
title: Submodule commit + parent repo pointer bump
kind: workflow
memory_scope: procedural
memory_strategy: hierarchical
update_strategy: merge_append
confidence: high
applies_to:
  - "*/llm_wiki_prompt_packet*"
  - "*/pk-skills1*"
  - "git submodule*"
created_at: 2026-04-21
---

# Submodule commit + parent repo pointer bump

## Trigger

Use when changes exist inside a submodule (`deps/pk-skills1` or similar) that need to reach the remote, AND the parent repo's recorded submodule pointer also needs to advance.

## Preconditions

- You are in the submodule directory (or can `cd` to it)
- The submodule has a remote configured (`git remote -v` shows an `origin`)
- The parent repo's `.gitmodules` lists the submodule path
- You have push access to both remotes

## Fast path

```bash
# 1. Stage and commit submodule changes
git add <changed-files>
git commit -m "<message>"

# 2. If remote has diverged (rejected push), rebase first
git pull --rebase && git push

# 3. Return to parent repo and bump the submodule pointer
cd ..  # or navigate to parent root
git add deps/pk-skills1   # or whichever submodule path
git commit -m "chore: bump deps/<submodule> to <short-sha>"
git push
```

## Failure modes

- **Push rejected (non-fast-forward)**: remote has commits you don't have. Run `git pull --rebase` inside the submodule first, then push. The rebase also picks up any new tags.
- **Parent commit without submodule changes staged**: forgetting `git add deps/<submodule>` in the parent means the pointer stays stale. Always verify with `git status` in the parent before committing.
- **Committing from wrong directory**: always confirm you are in the submodule root when staging submodule files, and in the parent root when bumping the pointer.
- **Dirty untracked files in submodule**: untracked files don't block a commit but do show in parent `git status` as `(untracked content)`. Stage them explicitly or add them to the submodule's `.gitignore`.

## Durable facts

- The parent repo only stores a SHA pointer to the submodule, not its contents. Both repos must be pushed independently.
- `git pull --rebase` inside a submodule is safe when remote has only additive changes (no force-push history).
- A newly published tag on the remote (`* [new tag]`) does not block the rebase; it is fetched automatically.

## Skip steps estimate

Saves ~3 steps vs. discovering the non-fast-forward rejection mid-push and then diagnosing the rebase flow manually.
