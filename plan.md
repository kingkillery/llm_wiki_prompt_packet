# LLM Wiki Prompt Packet Plan

## Current State

- `main` is clean and synced with `origin/main`.
- The model pool (LM Studio local + OpenRouter free + SiliconFlow cheap) is configured and probed.
- The advertised `wiki-bootstrap` command is merged.
- Root `scripts/` helpers are merged.
- CI and Docker Publish are green on `main`.

## Model Strategy (Background Operation)

Run sub-agents and auto-updates continuously using a tiered model pool:

| Tier | Provider | Models | Purpose |
|---|---|---|---|
| Local (free) | LM Studio | `nvidia/nemotron-3-nano-4b` | Priority slot for skill summaries, log entries, and low-latency tasks |
| Free remote | OpenRouter | `deepseek/deepseek-chat-v4-flash:free` | Fallback when local is offline; zero-cost inference |
| Cheap remote | SiliconFlow | `deepseek-ai/DeepSeek-V4-Flash`, `tencent/Hy3-preview`, `google/gemma-4-26B-A4B-it` | Higher-capacity tasks when free tiers are exhausted |

- Rotator uses round-robin across the active pool.
- LM Studio is probed at startup and skipped silently if offline.
- OpenRouter free tier acts as backstop for 429/rate-limit events.
- Exponential backoff (5-120s) with jitter prevents hammering any single provider.

## Recommended Next Steps

1. Validate a clean download/install path from the README on a fresh temp checkout.
2. Run the root script smoke commands from the fresh checkout.
3. Confirm the dashboard server and wiki auto-updater run continuously in the background.
4. Confirm `wiki-bootstrap` works from the installed `llm-wiki-skills` guidance path.
5. Decide whether to keep or retire the preserved local stash from the previous cleanup.
6. Start the dashboard server (`python scripts/dashboard_server.py --port 8183`) and wiki auto-update loop for continuous background operation.

## Verification Targets

- `python scripts/llm_wiki_packet.py check`
- `python scripts/llm_wiki_packet.py context --task "fresh install smoke"`
- `python scripts/llm_wiki_skill_mcp.py wiki-bootstrap --help`
- GitHub Actions CI on `main`

## Open Decision

The remaining local stash contains preserved project patch state from before the cleanup. It should be inspected before applying or deleting.

## Stash Inspection Result

`stash@{0}` was inspected without applying it. It touches 21 original files and overlaps heavily with the runtime, Docker, docs, and `llm-wiki-skills` work that has since been merged.

Do not apply it wholesale. Compared with current `main`, it would also remove or roll back newer merged files and tests such as the packet-owned Kade `HUMAN.md` fallback, `wiki-bootstrap` command tests, and CI portability fixes.

Recommendation: keep the stash only as a reference while cherry-picking any still-useful ideas manually. Likely candidates to review later are `.dockerignore` hardening and documentation wording.
