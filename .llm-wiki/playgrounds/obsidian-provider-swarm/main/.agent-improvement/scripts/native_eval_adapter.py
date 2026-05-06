from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def _load_target_modules(repo_root: Path):
    sys.path.insert(0, str(repo_root))
    import agents.agents as agent_registry  # type: ignore
    from gym_anything.api import from_config  # type: ignore

    return agent_registry, from_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one native Gym-Anything agent evaluation and emit normalized JSON.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--env-dir", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--agent-args", default="{}")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--output-json", required=True)
    return parser


def _safe_read_summary(summary_path: Path) -> dict[str, Any]:
    if not summary_path.exists():
        return {}
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def run_native_eval(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    agent_registry, from_config = _load_target_modules(repo_root)
    agent_args = json.loads(args.agent_args)

    env = from_config(args.env_dir, task_id=args.task)
    episode_dir = None
    step_count = 0
    info: dict[str, Any] = {}
    start = time.time()

    try:
        env.reset(seed=args.seed)
        env.set_episode_limits(max_steps=args.steps, timeout_sec=86400)
        episode_dir = env.episode_dir
        task_description = env.task_spec.description if env.task_spec else args.task
        agent_cls = getattr(agent_registry, args.agent)
        agent = agent_cls(agent_args=agent_args, verbose=False, debug=False)
        agent.init(
            task_description=task_description,
            display_resolution=env.env_spec.observation[0].resolution,
            save_path=env.episode_dir,
        )

        action_outputs = []
        obs = env.capture_observation()
        done = False

        for _ in range(env.max_steps):
            step_count += 1
            actions = agent.step(obs, action_outputs)
            action_outputs = []
            for action in actions:
                obs, _reward, done, info = env.step(action["actions"])
                action_result = info.get(
                    "action_result",
                    {
                        "action": "other",
                        "output": "Executed the action",
                    },
                )
                action_outputs.append(
                    {
                        **action_result,
                        "tool_id": action.get("tool_id", "unknown-tool"),
                    }
                )
            if getattr(agent, "done", False) or done:
                _obs, _reward, _done, info = env.step([], mark_done=True)
                break

        if "verifier" in info and info["verifier"] is None and episode_dir:
            info = _safe_read_summary(Path(episode_dir) / "summary.json")
        agent.finish(info=info)
    finally:
        env.close()

    duration = time.time() - start
    summary_path = Path(episode_dir) / "summary.json" if episode_dir else None
    summary = _safe_read_summary(summary_path) if summary_path else {}
    verifier = info.get("verifier") or summary.get("verifier")
    verifier_passed = bool(verifier and verifier.get("passed"))
    verifier_score = verifier.get("score") if isinstance(verifier, dict) else None
    feedback = verifier.get("feedback") if isinstance(verifier, dict) else None

    return {
        "agent_name": args.agent,
        "adapter_type": "native-gym-agent",
        "env_dir": args.env_dir,
        "task_id": args.task,
        "step_count": step_count,
        "duration_sec": round(duration, 3),
        "episode_dir": str(episode_dir) if episode_dir else None,
        "summary_path": str(summary_path) if summary_path and summary_path.exists() else None,
        "success": verifier_passed,
        "verifier": verifier,
        "verifier_passed": verifier_passed,
        "verifier_score": verifier_score,
        "feedback": feedback,
        "error": None,
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run_native_eval(args)
    except Exception as exc:
        result = {
            "agent_name": args.agent,
            "adapter_type": "native-gym-agent",
            "env_dir": args.env_dir,
            "task_id": args.task,
            "step_count": 0,
            "duration_sec": 0.0,
            "episode_dir": None,
            "summary_path": None,
            "success": False,
            "verifier": None,
            "verifier_passed": False,
            "verifier_score": None,
            "feedback": None,
            "error": str(exc),
        }
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
