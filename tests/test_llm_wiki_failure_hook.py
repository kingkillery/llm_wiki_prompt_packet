from __future__ import annotations

import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_failure_hook.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_failure_hook", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FailureHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_build_payload_marks_auth_failures_as_non_promoting(self) -> None:
        payload = self.module.build_payload(
            {
                "hook_event_name": "PostToolUseFailure",
                "tool_name": "Bash",
                "tool_input": {"command": "git fetch"},
                "error": "Authentication failed for remote",
                "transcript_path": "transcript.md",
                "session_id": "session-1",
            }
        )

        assert payload is not None
        self.assertEqual(payload["tool_name"], "Bash")
        self.assertFalse(payload["auto_promote"])
        self.assertEqual(payload["source_type"], "claude_hook_post_tool_use_failure")
        self.assertIn("git fetch", payload["goal"])

    def test_main_records_and_attempts_promotion(self) -> None:
        recorded_payloads: list[dict[str, object]] = []
        promotions: list[tuple[str, int, bool]] = []

        class FakeCollector:
            def __init__(self, workspace: str) -> None:
                self.workspace = workspace

            def record(self, payload: dict[str, object]) -> dict[str, object]:
                recorded_payloads.append(payload)
                return {"event": {"fingerprint": "fingerprint-1"}}

            def promote(self, fingerprint: str, limit: int, force: bool) -> dict[str, object]:
                promotions.append((fingerprint, limit, force))
                return {"promoted": []}

        stdin = io.StringIO(
            json.dumps(
                {
                    "hook_event_name": "PostToolUseFailure",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "README.md"},
                    "error": "Patch rejected",
                    "session_id": "session-2",
                }
            )
        )
        stdout = io.StringIO()

        with mock.patch.object(self.module, "FailureCollector", FakeCollector):
            with mock.patch.object(self.module.sys, "argv", ["hook", "--workspace", "workspace"]):
                with mock.patch.object(self.module.sys, "stdin", stdin):
                    with mock.patch.object(self.module.sys, "stdout", stdout):
                        result = self.module.main()

        self.assertEqual(result, 0)
        self.assertEqual(recorded_payloads[0]["tool_name"], "Edit")
        self.assertEqual(promotions, [("fingerprint-1", 1, False)])
        self.assertIn('"continue": true', stdout.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
