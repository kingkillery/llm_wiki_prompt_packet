from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_WRAPPER = REPO_ROOT / "support" / "scripts" / "setup_llm_wiki_memory.ps1"
CHECK_WRAPPER = REPO_ROOT / "installers" / "assets" / "vault" / "scripts" / "check_llm_wiki_memory.ps1"
CMD_WRAPPER = REPO_ROOT / "support" / "scripts" / "run_llm_wiki_agent.cmd"


def powershell_executable() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


class WindowsWrapperRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "argv.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def env_with_shims(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = str(self.bin_dir) + os.pathsep + env.get("PATH", "")
        env["LLM_WIKI_TEST_LOG"] = str(self.log_path)
        return env

    def write_runtime_probe(self, destination: Path) -> None:
        destination.write_text(
            textwrap.dedent(
                """
                import json
                import os
                import sys
                from pathlib import Path

                Path(os.environ["LLM_WIKI_TEST_LOG"]).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    def write_python_cmd_shim(self, name: str) -> None:
        shim_path = self.bin_dir / name
        if name.lower().startswith("py."):
            content = textwrap.dedent(
                f"""
                @echo off
                "{sys.executable}" %2 %3 %4 %5 %6 %7 %8 %9
                """
            ).strip()
        else:
            content = textwrap.dedent(
                f"""
                @echo off
                "{sys.executable}" %*
                """
            ).strip()
        shim_path.write_text(content + "\n", encoding="ascii")

    def run_powershell_wrapper(self, source_wrapper: Path, mode: str, *extra_args: str) -> list[str]:
        powershell = powershell_executable()
        if not powershell:
            self.skipTest("PowerShell is not available")

        wrapper_dir = self.root / mode
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper_path = wrapper_dir / source_wrapper.name
        wrapper_path.write_text(source_wrapper.read_text(encoding="utf-8"), encoding="utf-8")
        self.write_runtime_probe(wrapper_dir / "llm_wiki_memory_runtime.py")
        self.write_python_cmd_shim("python.cmd")

        completed = subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper_path), *extra_args],
            cwd=str(self.root),
            env=self.env_with_shims(),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(f"wrapper failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
        return json.loads(self.log_path.read_text(encoding="utf-8"))

    def test_setup_wrapper_preserves_legacy_powershell_parameters(self) -> None:
        argv = self.run_powershell_wrapper(
            SETUP_WRAPPER,
            "setup",
            "-WorkspaceRoot",
            r"C:\workspace",
            "-QmdSource",
            r"C:\pk-qmd",
            "-SkipQmd",
            "-VerifyOnly",
        )

        self.assertEqual(
            argv,
            [
                "setup",
                "--workspace",
                r"C:\workspace",
                "--qmd-source",
                r"C:\pk-qmd",
                "--skip-qmd",
                "--verify-only",
            ],
        )

    def test_check_wrapper_preserves_legacy_powershell_parameters(self) -> None:
        argv = self.run_powershell_wrapper(
            CHECK_WRAPPER,
            "check",
            "-WorkspaceRoot",
            r"C:\workspace",
            "-ConfigPath",
            r"C:\workspace\.llm-wiki\config.json",
            "-SkipGitvizz",
        )

        self.assertEqual(
            argv,
            [
                "check",
                "--workspace",
                r"C:\workspace",
                "--config-path",
                r"C:\workspace\.llm-wiki\config.json",
                "--skip-gitvizz",
            ],
        )

    def test_cmd_wrapper_preserves_exclamation_marks_in_forwarded_arguments(self) -> None:
        wrapper_dir = self.root / "cmd"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper_path = wrapper_dir / CMD_WRAPPER.name
        wrapper_path.write_text(CMD_WRAPPER.read_text(encoding="utf-8"), encoding="utf-8")
        self.write_runtime_probe(wrapper_dir / "llm_wiki_agent_failure_capture.py")
        self.write_python_cmd_shim("py.cmd")

        completed = subprocess.run(
            ["cmd", "/c", str(wrapper_path), "--agent", "codex", "--", "Hello!", "!VAR!"],
            cwd=str(self.root),
            env=self.env_with_shims(),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(f"wrapper failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")

        argv = json.loads(self.log_path.read_text(encoding="utf-8"))
        self.assertEqual(argv, ["--agent", "codex", "--", "Hello!", "!VAR!"])


if __name__ == "__main__":
    unittest.main()
