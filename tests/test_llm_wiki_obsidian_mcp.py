from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_obsidian_mcp.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_obsidian_mcp", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ObsidianMcpWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / ".llm-wiki").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_environment_vault_path_overrides_workspace_fallback(self) -> None:
        tool = self.workspace / ".llm-wiki" / "tools" / "obsidian-mcp" / "node_modules" / ".bin" / "mcpvault.cmd"
        tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_text("@echo off\r\n", encoding="ascii")
        vault = self.workspace / "Kade-HQ"
        vault.mkdir()

        with mock.patch.object(self.module.sys, "argv", ["prog", "--workspace", str(self.workspace)]):
            with mock.patch.dict(self.module.os.environ, {"OBSIDIAN_VAULT_PATH": str(vault)}, clear=True):
                with mock.patch.object(self.module.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
                    result = self.module.main()

        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0], [str(tool), str(vault.resolve(strict=False))])

    def test_cli_vault_argument_takes_precedence_over_environment(self) -> None:
        tool = self.workspace / ".llm-wiki" / "tools" / "obsidian-mcp" / "node_modules" / ".bin" / "mcpvault.cmd"
        tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_text("@echo off\r\n", encoding="ascii")
        env_vault = self.workspace / "EnvVault"
        cli_vault = self.workspace / "CliVault"
        env_vault.mkdir()
        cli_vault.mkdir()

        with mock.patch.object(self.module.sys, "argv", ["prog", "--workspace", str(self.workspace), "--vault", str(cli_vault)]):
            with mock.patch.dict(self.module.os.environ, {"OBSIDIAN_VAULT_PATH": str(env_vault)}, clear=True):
                with mock.patch.object(self.module.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
                    result = self.module.main()

        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0], [str(tool), str(cli_vault.resolve(strict=False))])

    def test_configured_vault_path_is_used_when_environment_is_absent(self) -> None:
        tool = self.workspace / ".llm-wiki" / "tools" / "obsidian-mcp" / "node_modules" / ".bin" / "mcpvault.cmd"
        tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_text("@echo off\r\n", encoding="ascii")
        vault = self.workspace / "ConfiguredVault"
        vault.mkdir()
        config_path = self.workspace / ".llm-wiki" / "config.json"
        config_path.write_text(json.dumps({"obsidian": {"vault_path": str(vault)}}), encoding="utf-8")

        with mock.patch.object(self.module.sys, "argv", ["prog", "--workspace", str(self.workspace)]):
            with mock.patch.dict(self.module.os.environ, {}, clear=True):
                with mock.patch.object(self.module.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
                    result = self.module.main()

        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0], [str(tool), str(vault.resolve(strict=False))])


if __name__ == "__main__":
    unittest.main()
