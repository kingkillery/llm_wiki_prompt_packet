# Benchmark: Packet vs. Baseline (M3)

> **Goal:** Validate that the `llm-wiki-memory` stack improves task completion and reduces step count on repeated tasks versus a no-memory baseline.
> **Target:** 2026-05-30

---

## Conditions

| Condition | Memory setup | Expected behavior |
|---|---|---|
| **A: Packet** | Full stack: skills, auto-reducer, classifier, recency decay, graph traversal | Step count drops on repetition 2+ |
| **B: Baseline** | No memory; raw context only | No learning across episodes |

Condition B (Mem0) is deferred until Mem0 integration is wired. For now we compare Packet vs. Baseline.

---

## Task selection

Use the `cua_world/pokemon_agent_env` harness or a synthetic multi-step task that rewards skill reuse.

Ideal task properties:
- Multi-step (≥5 actions)
- Repeatable with identical starting state
- Benefits from procedural memory (same workflow each time)
- Observable failure modes that skills can prevent

Candidate: `start_server_capture_state@1` or a custom `git-workflow` task.

---

## Metrics

| Metric | How measured | Success threshold |
|---|---|---|
| Task completion rate | % of episodes that reach success state | Packet ≥ baseline |
| Steps to completion | Mean actions taken | Packet ≤ baseline |
| Steps on repetition 2 | Actions on second run of same task | Packet shows ≥30% reduction vs baseline |
| Steps on repetition 3 | Actions on third run | Packet shows ≥30% reduction vs baseline |
| Memory store growth | Number of skills/facts created | Signal/noise ratio > 0.5 |

---

## Protocol

1. **Warm-up:** Run 1 episode of the task to seed the packet's skill library (Condition A only).
2. **Record:** Run 20 episodes per condition.
3. **Measure:** Capture steps, completion, errors, and skill usage.
4. **Analyze:** Welch's t-test on step counts between conditions.

---

## Running

```bash
# Packet condition
python benchmarks/roadmap-m3-2026/harness.py --condition packet --episodes 20

# Baseline condition
python benchmarks/roadmap-m3-2026/harness.py --condition baseline --episodes 20

# Analysis
python benchmarks/roadmap-m3-2026/harness.py --analyze results/
```

---

## Deliverables

- `report.md` — statistical analysis and interpretation
- `results/` — raw JSONL per episode
- `artifacts/` — screenshots, logs, skill captures
