from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_packet.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_packet", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PacketCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_command_init_invokes_workspace_installer_with_expected_flags(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            args = self.module.build_parser().parse_args(
                [
                    "init",
                    "--project-root",
                    project_dir,
                    "--packet-root",
                    str(REPO_ROOT),
                    "--home-root",
                    home_dir,
                    "--allow-global-tool-install",
                    "--enable-gitvizz",
                    "--force",
                ]
            )

            completed = mock.Mock(returncode=0)
            with mock.patch.object(self.module, "python_command", return_value=["python"]):
                with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run_mock:
                    exit_code = self.module.main_from_args(args)

            self.assertEqual(exit_code, 0)
            invoked = run_mock.call_args.args[0]
            self.assertEqual(invoked[0], "python")
            self.assertIn(str(REPO_ROOT / "installers" / "install_g_kade_workspace.py"), invoked)
            self.assertIn("--install-home-skills", invoked)
            self.assertIn("--allow-global-tool-install", invoked)
            self.assertIn("--enable-gitvizz", invoked)
            self.assertIn("--force", invoked)

    def test_command_check_uses_runtime_script_and_skips_gitvizz_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            (workspace_root / "scripts").mkdir(parents=True, exist_ok=True)
            (workspace_root / "scripts" / "llm_wiki_memory_runtime.py").write_text("print('ok')\n", encoding="utf-8")

            args = self.module.build_parser().parse_args(["check", "--workspace-root", workspace_dir])

            completed = mock.Mock(returncode=0)
            with mock.patch.object(self.module, "python_command", return_value=["python"]):
                with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run_mock:
                    exit_code = self.module.main_from_args(args)

            self.assertEqual(exit_code, 0)
            invoked = run_mock.call_args.args[0]
            self.assertEqual(
                invoked,
                [
                    "python",
                    str(workspace_root / "scripts" / "llm_wiki_memory_runtime.py"),
                    "check",
                    "--skip-gitvizz",
                ],
            )

    def test_command_pokemon_benchmark_prefers_workspace_script(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            (workspace_root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
            (workspace_root / "scripts").mkdir(parents=True, exist_ok=True)
            adapter = workspace_root / "scripts" / "pokemon_benchmark_adapter.py"
            adapter.write_text("print('ok')\n", encoding="utf-8")

            args = self.module.build_parser().parse_args(
                ["pokemon-benchmark", "smoke", "--workspace-root", workspace_dir, "--seed", "99"]
            )

            completed = mock.Mock(returncode=0)
            with mock.patch.object(self.module, "python_command", return_value=["python"]):
                with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run_mock:
                    exit_code = self.module.main_from_args(args)

            self.assertEqual(exit_code, 0)
            invoked = run_mock.call_args.args[0]
            self.assertEqual(invoked[0], "python")
            self.assertEqual(invoked[1], str(adapter))
            self.assertIn("smoke", invoked)
            self.assertIn("--seed", invoked)
            self.assertIn("99", invoked)

    def test_command_pokemon_benchmark_accepts_flag_mode(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            (workspace_root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
            (workspace_root / "scripts").mkdir(parents=True, exist_ok=True)
            adapter = workspace_root / "scripts" / "pokemon_benchmark_adapter.py"
            adapter.write_text("print('ok')\n", encoding="utf-8")

            args = self.module.build_parser().parse_args(
                ["pokemon-benchmark", "--mode", "smoke", "--workspace-root", workspace_dir]
            )

            completed = mock.Mock(returncode=0)
            with mock.patch.object(self.module, "python_command", return_value=["python"]):
                with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run_mock:
                    exit_code = self.module.main_from_args(args)

            self.assertEqual(exit_code, 0)
            invoked = run_mock.call_args.args[0]
            self.assertEqual(invoked[0], "python")
            self.assertEqual(invoked[1], str(adapter))
            self.assertIn("smoke", invoked)

    def test_context_command_returns_compact_bundle_with_expansion_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            (workspace_root / "AGENTS.md").write_text("# Agents\n\nUse pk-qmd for evidence.\n", encoding="utf-8")
            (workspace_root / "LLM_WIKI_MEMORY.md").write_text("# Memory\n\nSource evidence beats memory.\n", encoding="utf-8")
            (workspace_root / "wiki" / "syntheses").mkdir(parents=True, exist_ok=True)
            (workspace_root / "wiki" / "syntheses" / "retrieval.md").write_text(
                "# Retrieval\n\nHybrid search should be explicit evidence expansion.\n",
                encoding="utf-8",
            )

            args = self.module.build_parser().parse_args(
                ["context", "--workspace-root", workspace_dir, "--task", "hybrid search evidence", "--json"]
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = self.module.main_from_args(args)

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["command"], "llm-wiki-packet context")
            self.assertEqual(payload["mode"], "default")
            self.assertIn("AGENTS.md", payload["instructions"])
            self.assertTrue(payload["evidence"])
            self.assertTrue(any("evidence" in item for item in payload["expansion_suggestions"]))

    def test_evidence_command_searches_broadly_without_context_bloat(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            (workspace_root / "wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / "wiki" / "note.md").write_text(
                "GitVizz topology evidence belongs behind explicit graph expansion.\n",
                encoding="utf-8",
            )

            args = self.module.build_parser().parse_args(
                ["evidence", "--workspace-root", workspace_dir, "--query", "GitVizz topology evidence", "--json"]
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = self.module.main_from_args(args)

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["command"], "llm-wiki-packet evidence")
            self.assertEqual(payload["policy"]["retrieval"], "broad search is explicit")
            self.assertEqual(payload["evidence"][0]["source"], "wiki/note.md")

    def test_evidence_command_searches_source_directories(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            (workspace_root / "support" / "scripts").mkdir(parents=True, exist_ok=True)
            (workspace_root / "support" / "scripts" / "helper.py").write_text(
                "def helper():\n    return 'source topology evidence marker'\n",
                encoding="utf-8",
            )

            args = self.module.build_parser().parse_args(
                ["evidence", "--workspace-root", workspace_dir, "--query", "source topology evidence marker", "--json"]
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = self.module.main_from_args(args)

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            sources = [item["source"] for item in payload["evidence"]]
            self.assertIn("support/scripts/helper.py", sources)

    def test_run_lifecycle_commands_create_gated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            (workspace_root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")

            manifest_args = self.module.build_parser().parse_args(
                [
                    "manifest",
                    "--workspace-root",
                    workspace_dir,
                    "--run-id",
                    "run-1",
                    "--task",
                    "test memory loop",
                    "--success-criteria",
                    "creates reducer packet",
                    "--json",
                ]
            )
            reduce_args = self.module.build_parser().parse_args(
                [
                    "reduce",
                    "--workspace-root",
                    workspace_dir,
                    "--run-id",
                    "run-1",
                    "--text",
                    "The packet should use explicit evidence expansion. See https://example.com/evidence.",
                    "--json",
                ]
            )
            evaluate_args = self.module.build_parser().parse_args(
                ["evaluate", "--workspace-root", workspace_dir, "--run-id", "run-1", "--task-success", "pass", "--json"]
            )
            improve_blocked_args = self.module.build_parser().parse_args(
                ["improve", "--workspace-root", workspace_dir, "--run-id", "run-1", "--json"]
            )
            improve_accept_args = self.module.build_parser().parse_args(
                [
                    "improve",
                    "--workspace-root",
                    workspace_dir,
                    "--run-id",
                    "run-1",
                    "--benchmark-passed",
                    "--no-regression",
                    "--json",
                ]
            )

            for args in (manifest_args, reduce_args, evaluate_args, improve_blocked_args, improve_accept_args):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(self.module.main_from_args(args), 0)

            run_root = workspace_root / ".llm-wiki" / "skill-pipeline" / "runs" / "run-1"
            self.assertTrue((run_root / "manifest.json").exists())
            self.assertTrue((run_root / "reducer_packet.md").exists())
            self.assertTrue((run_root / "claims.json").exists())
            self.assertTrue((run_root / "evaluation.json").exists())
            proposal = json.loads((run_root / "improvement_proposal.json").read_text(encoding="utf-8"))
            self.assertEqual(proposal["status"], "accepted")

    def test_promote_command_is_decision_only_until_apply(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace_root = Path(workspace_dir)
            (workspace_root / ".llm-wiki").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".llm-wiki" / "config.json").write_text("{}", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.module.main_from_args(
                    self.module.build_parser().parse_args(
                        [
                            "reduce",
                            "--workspace-root",
                            workspace_dir,
                            "--run-id",
                            "run-2",
                            "--text",
                            "Durable fact needs review before promotion.",
                        ]
                    )
                )

            args = self.module.build_parser().parse_args(
                ["promote", "--workspace-root", workspace_dir, "--run-id", "run-2", "--target", "semantic", "--json"]
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(self.module.main_from_args(args), 0)
            payload = json.loads(stdout.getvalue())
            self.assertFalse(payload["decision"]["applied"])
            self.assertFalse((workspace_root / "wiki" / "syntheses" / "run-2.md").exists())


if __name__ == "__main__":
    unittest.main()
