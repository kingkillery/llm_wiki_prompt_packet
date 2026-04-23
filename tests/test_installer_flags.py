#!/usr/bin/env python3
"""Tests for installer CLI flags (M4)."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = REPO_ROOT / "install.sh"
INSTALL_PS1 = REPO_ROOT / "install.ps1"


class TestInstallerFlags(unittest.TestCase):
    def test_install_sh_has_unattended_flag(self) -> None:
        text = INSTALL_SH.read_text(encoding="utf-8")
        self.assertIn("--unattended", text)
        self.assertIn("LLM_WIKI_UNATTENDED", text)

    def test_install_ps1_has_unattended_flag(self) -> None:
        text = INSTALL_PS1.read_text(encoding="utf-8")
        self.assertIn("[switch]$Unattended", text)

    def test_install_ps1_uses_short_temp_extract_root(self) -> None:
        text = INSTALL_PS1.read_text(encoding="utf-8")
        self.assertIn('"lwpk-" + [guid]::NewGuid().ToString("N").Substring(0, 12)', text)

    def test_install_ps1_skips_gitvizz_in_wire_repo_health_check_by_default(self) -> None:
        text = INSTALL_PS1.read_text(encoding="utf-8")
        self.assertIn('$Mode -eq "g-kade" -and $env:LLM_WIKI_SKIP_GITVIZZ -ne "0"', text)
        self.assertIn('$checkArgs += "-SkipGitvizz"', text)

    @unittest.skipIf(sys.platform == "win32", "bash not available on Windows")
    def test_install_sh_unattended_skips_prompt(self) -> None:
        """Run install.sh --help to verify it accepts --unattended."""
        result = subprocess.run(
            ["bash", str(INSTALL_SH), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--unattended", result.stdout)

    def test_install_sh_skips_gitvizz_in_wire_repo_health_check_by_default(self) -> None:
        text = INSTALL_SH.read_text(encoding="utf-8")
        self.assertIn('[[ "$INSTALL_MODE" == "g-kade" && "${LLM_WIKI_SKIP_GITVIZZ:-1}" != "0" ]]', text)
        self.assertIn('CHECK_ARGS+=(--skip-gitvizz)', text)

    def test_docker_compose_quickstart_exists(self) -> None:
        path = REPO_ROOT / "docker-compose.quickstart.yml"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("llm-wiki-quickstart", text)
        self.assertIn("8181", text)


if __name__ == "__main__":
    unittest.main()
