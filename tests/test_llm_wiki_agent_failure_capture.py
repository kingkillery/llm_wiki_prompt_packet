from __future__ import annotations

import argparse
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_agent_failure_capture.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_agent_failure_capture", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AgentFailureCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_infer_mode_classifies_supported_agent_surfaces(self) -> None:
        self.assertEqual(self.module.infer_mode("claude", ["--print", "summarize this"]), "noninteractive")
        self.assertEqual(self.module.infer_mode("claude", ["chat"]), "interactive")
        self.assertEqual(self.module.infer_mode("codex", ["exec", "review diff"]), "noninteractive")
        self.assertEqual(self.module.infer_mode("codex", []), "interactive")
        self.assertEqual(self.module.infer_mode("droid", ["exec", "analyze repo"]), "noninteractive")
        self.assertEqual(self.module.infer_mode("droid", ["chat"]), "interactive")
        self.assertEqual(self.module.infer_mode("pi", ["-p", "status"]), "noninteractive")
        self.assertEqual(self.module.infer_mode("pi", ["chat"]), "interactive")

    def test_default_workspace_root_uses_script_parent(self) -> None:
        self.assertEqual(self.module.default_workspace_root(), MODULE_PATH.parent.parent.resolve())

    def test_build_failure_payload_marks_auth_failures_non_promotable(self) -> None:
        payload = self.module.build_failure_payload(
            workspace=self.workspace,
            agent="droid",
            command=["droid", "exec", "analyze repo"],
            argv=["exec", "analyze repo"],
            mode="noninteractive",
            result={
                "returncode": 1,
                "stdout": "",
                "stderr": "Authentication failed for Factory account",
                "spawn_error": "",
            },
        )

        self.assertEqual(payload["agent"], "factory-droid")
        self.assertEqual(payload["error_class"], "droid_auth_failure")
        self.assertFalse(payload["auto_promote"])
        self.assertEqual(payload["source_type"], "droid_cli_process_wrapper")
        self.assertEqual(payload["benchmark"], "droid-cli-wrapper")

    def test_write_stream_text_falls_back_for_narrow_console_encodings(self) -> None:
        class Cp1252Target:
            def __init__(self) -> None:
                self.encoding = "cp1252"
                self.buffer = io.BytesIO()

            def write(self, text: str) -> int:
                encoded = text.encode(self.encoding)
                self.buffer.write(encoded)
                return len(text)

            def flush(self) -> None:
                return None

        target = Cp1252Target()

        self.module.write_stream_text(target, "Codex non‑interactive output\n")

        self.assertIn("non?interactive", target.buffer.getvalue().decode("cp1252"))

    def test_main_records_failed_run_and_promotes_matching_cluster(self) -> None:
        args = argparse.Namespace(
            workspace=str(self.workspace),
            agent="pi",
            mode="auto",
            command_name="",
            argv=["-p", "explain this diff"],
        )
        collector_instances: list[object] = []

        class FakeCollector:
            def __init__(self, workspace: str | Path) -> None:
                self.workspace = Path(workspace)
                self.recorded: list[dict[str, object]] = []
                self.promotions: list[dict[str, object]] = []

            def record(self, payload: dict[str, object]) -> dict[str, object]:
                self.recorded.append(payload)
                return {"event": {"fingerprint": "fp-123"}}

            def promote(self, **kwargs: object) -> dict[str, object]:
                self.promotions.append(kwargs)
                return {"status": "ok"}

        def collector_factory(workspace: str | Path) -> FakeCollector:
            instance = FakeCollector(workspace)
            collector_instances.append(instance)
            return instance

        with (
            mock.patch.object(self.module, "parse_args", return_value=args),
            mock.patch.object(self.module, "resolve_command_name", return_value="pi"),
            mock.patch.object(
                self.module,
                "run_command",
                return_value={
                    "returncode": 9,
                    "stdout": "",
                    "stderr": "Model backend crashed",
                    "spawn_error": "",
                },
            ),
            mock.patch.object(self.module, "FailureCollector", side_effect=collector_factory),
        ):
            returncode = self.module.main()

        self.assertEqual(returncode, 9)
        self.assertEqual(len(collector_instances), 1)
        collector = collector_instances[0]
        self.assertEqual(len(collector.recorded), 1)
        self.assertEqual(collector.recorded[0]["agent"], "pi-mono")
        self.assertEqual(collector.recorded[0]["error_class"], "pi_exit_9")
        self.assertEqual(collector.recorded[0]["source_type"], "pi_cli_process_wrapper")
        self.assertEqual(
            collector.promotions,
            [{"fingerprint": "fp-123", "limit": 1, "force": False}],
        )

    def test_main_skips_collection_for_successful_run(self) -> None:
        args = argparse.Namespace(
            workspace=str(self.workspace),
            agent="codex",
            mode="auto",
            command_name="",
            argv=["exec", "review diff"],
        )

        with (
            mock.patch.object(self.module, "parse_args", return_value=args),
            mock.patch.object(self.module, "resolve_command_name", return_value="codex"),
            mock.patch.object(
                self.module,
                "run_command",
                return_value={
                    "returncode": 0,
                    "stdout": "ok",
                    "stderr": "",
                    "spawn_error": "",
                },
            ),
            mock.patch.object(self.module, "FailureCollector") as collector_cls,
        ):
            returncode = self.module.main()

        self.assertEqual(returncode, 0)
        collector_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
