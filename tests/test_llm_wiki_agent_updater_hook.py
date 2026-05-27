from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "support" / "scripts" / "llm_wiki_agent_updater_hook.py"


class AgentUpdaterHookTests(unittest.TestCase):
    def test_disabled_hook_records_event_without_launching_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            env = dict(os.environ)
            env["LLM_WIKI_UPDATER_ENABLED"] = "0"
            payload = {"hook_event_name": "SessionStart", "source": "startup"}

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "codex",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            response = json.loads(completed.stdout)
            self.assertTrue(response["continue"])
            state = workspace / ".llm-wiki" / "state" / "agent-updater"
            self.assertTrue((state / "hook-events.jsonl").exists())
            audit = json.loads((state / "hook-events.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(audit["agent"], "codex")
            self.assertEqual(audit["event"], "SessionStart")
            self.assertEqual(audit["reason"], "disabled")
            self.assertTrue(list((state / "events").glob("*.json")))

    def test_inline_hook_runs_local_memory_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Remember that this repo should keep updater hooks enabled for Claude and Codex.",
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "claude",
                    "--inline",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            runs_path = workspace / ".llm-wiki" / "state" / "agent-updater" / "runs.jsonl"
            self.assertTrue(runs_path.exists())
            run = json.loads(runs_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(run["agent"], "claude")
            self.assertEqual(run["event"], "UserPromptSubmit")
            self.assertIn(run["memory_extract"]["status"], {"ok", "failed"})

    def test_codex_event_name_and_input_payload_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = {
                "event_name": "UserPromptSubmit",
                "input": "Remember that Codex hook payloads may use input instead of prompt.",
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "codex",
                    "--inline",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            event_files = list((workspace / ".llm-wiki" / "state" / "agent-updater" / "events").glob("*.json"))
            self.assertEqual(len(event_files), 1)
            event = json.loads(event_files[0].read_text(encoding="utf-8"))
            self.assertEqual(event["hook_event_name"], "UserPromptSubmit")


if __name__ == "__main__":
    unittest.main()
