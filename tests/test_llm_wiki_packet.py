from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
