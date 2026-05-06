from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ENV_TEMPLATE = {
    "id": "{env_name}_env@0.1",
    "version": "0.1",
    "base": "ubuntu-gnome-systemd_highres",
    "description": "TODO: describe the target software environment",
    "resources": {
        "cpu": 4,
        "mem_gb": 8,
        "gpu": 0,
        "net": True,
    },
    "observation": [
        {
            "type": "rgb_screen",
            "fps": 10,
            "resolution": [1920, 1080],
            "inline": False,
        }
    ],
    "action": [
        {"type": "mouse"},
        {"type": "keyboard"},
    ],
    "synchronous": True,
    "step_cycle_ms": 200,
    "recording": {
        "enable": False,
        "output_dir": "benchmarks/cua_world/environments/{env_name}_env/artifacts",
        "video_fps": 10,
        "video_resolution": [1920, 1080],
        "video_codec": "libx264",
        "video_crf": 23,
    },
    "tags": ["linux", "todo"],
}

TASK_TEMPLATE = {
    "id": "{task_id}@1",
    "version": "1.0",
    "env_id": "{env_name}_env@0.1",
    "description": "TODO: describe the user-visible task",
    "difficulty": "medium",
    "init": {
        "timeout_sec": 180,
        "max_steps": 30,
        "reward_type": "sparse",
    },
    "hooks": {
        "pre_task": "/workspace/tasks/{task_id}/setup_task.sh",
        "post_task": "/workspace/tasks/{task_id}/export_result.sh",
    },
    "metadata": {},
    "success": {
        "mode": "program",
        "spec": {
            "program": "verifier.py::verify_task",
        },
    },
}

SETUP_SH = """#!/usr/bin/env bash
set -euo pipefail

echo "TODO: prepare the software state for this task"
"""

EXPORT_SH = """#!/usr/bin/env bash
set -euo pipefail

echo "TODO: export any artifacts needed by the verifier"
"""

VERIFIER_PY = """from __future__ import annotations


def verify_task(*args, **kwargs):
    return {
        "passed": False,
        "score": 0,
        "feedback": "TODO: implement task-specific verification logic",
    }
"""


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scaffold(gym_repo: Path, env_name: str, task_id: str) -> list[Path]:
    env_slug = f"{env_name}_env"
    env_root = gym_repo / "benchmarks" / "cua_world" / "environments" / env_slug
    task_root = env_root / "tasks" / task_id

    env_payload = json.loads(json.dumps(ENV_TEMPLATE).replace("{env_name}", env_name))
    task_payload = json.loads(
        json.dumps(TASK_TEMPLATE).replace("{env_name}", env_name).replace("{task_id}", task_id)
    )

    created = [
        env_root / "env.json",
        task_root / "task.json",
        task_root / "setup_task.sh",
        task_root / "export_result.sh",
        task_root / "verifier.py",
    ]
    _write_json(created[0], env_payload)
    _write_json(created[1], task_payload)
    _write_text(created[2], SETUP_SH)
    _write_text(created[3], EXPORT_SH)
    _write_text(created[4], VERIFIER_PY)
    return created


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold a starter Gym-Anything environment and task.")
    parser.add_argument("--gym-repo", required=True)
    parser.add_argument("--env-name", required=True)
    parser.add_argument("--task-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    gym_repo = Path(args.gym_repo)
    if not gym_repo.is_dir():
        print(f"Gym repo does not exist or is not a directory: {gym_repo}", file=sys.stderr)
        return 1
    created = scaffold(gym_repo, args.env_name, args.task_id)
    print("Scaffolded Gym-Anything starter files:")
    for path in created:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
