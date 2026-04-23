#!/usr/bin/env python3
"""Benchmark harness for M3: Packet vs Baseline.

Usage:
    python harness.py --condition packet|baseline --episodes 20 --task <name>
    python harness.py --analyze results/
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_episode(condition: str, task: str, episode: int, workspace: Path) -> dict:
    """Run a single episode and return metrics.

    This is a stub. In production it would invoke the actual agent harness
    (cua_world, local CLI wrapper, or MCP tool sequence).
    """
    # Simulate: packet condition gets faster on repetition
    base_steps = random.randint(8, 14)
    if condition == "packet":
        # Simulate learning curve
        if episode == 0:
            steps = base_steps
        elif episode == 1:
            steps = int(base_steps * 0.8)
        else:
            steps = int(base_steps * 0.65)
        success = random.random() > 0.1
    else:
        steps = base_steps
        success = random.random() > 0.15

    return {
        "episode": episode,
        "condition": condition,
        "task": task,
        "steps": steps,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def cmd_run(args: argparse.Namespace) -> int:
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for i in range(args.episodes):
        result = run_episode(args.condition, args.task, i, Path(args.workspace))
        results.append(result)
        print(f"Episode {i+1}/{args.episodes}: steps={result['steps']} success={result['success']}")

    path = out_dir / f"{args.condition}_{args.task}_{args.episodes}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"Results written to {path}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    results_dir = Path(args.results_dir)
    all_results: list[dict] = []
    for path in results_dir.glob("*.jsonl"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    all_results.append(json.loads(line))

    if not all_results:
        print("No results found.", file=sys.stderr)
        return 1

    by_condition: dict[str, list[dict]] = {}
    for r in all_results:
        by_condition.setdefault(r["condition"], []).append(r)

    print("# Benchmark Report\n")
    for condition, items in by_condition.items():
        steps = [r["steps"] for r in items]
        successes = [r["success"] for r in items]
        print(f"## Condition: {condition}")
        print(f"- Episodes: {len(items)}")
        print(f"- Completion rate: {sum(successes)/len(successes):.1%}")
        print(f"- Mean steps: {statistics.mean(steps):.1f}")
        print(f"- Median steps: {statistics.median(steps):.1f}")
        if len(steps) > 1:
            print(f"- Stdev steps: {statistics.stdev(steps):.1f}")
        print()

    # Simple comparison if both conditions present
    if "packet" in by_condition and "baseline" in by_condition:
        packet_steps = [r["steps"] for r in by_condition["packet"]]
        baseline_steps = [r["steps"] for r in by_condition["baseline"]]
        reduction = (statistics.mean(baseline_steps) - statistics.mean(packet_steps)) / statistics.mean(baseline_steps)
        print(f"## Comparison")
        print(f"- Step reduction (packet vs baseline): {reduction:.1%}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="M3 Benchmark Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run episodes")
    run_p.add_argument("--condition", choices=["packet", "baseline"], required=True)
    run_p.add_argument("--task", default="git-workflow", help="Task name")
    run_p.add_argument("--episodes", type=int, default=20)
    run_p.add_argument("--workspace", default=str(Path.cwd()))
    run_p.add_argument("--output", default="benchmarks/roadmap-m3-2026/results")
    run_p.add_argument("--stub", action="store_true", help="Use simulated data for demonstration")

    analyze_p = sub.add_parser("analyze", help="Analyze results")
    analyze_p.add_argument("results_dir", help="Directory containing JSONL result files")

    args = parser.parse_args()
    if args.command == "run":
        return cmd_run(args)
    return cmd_analyze(args)


if __name__ == "__main__":
    sys.exit(main())
