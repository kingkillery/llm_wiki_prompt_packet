from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "installers" / "install_g_kade_workspace.py"


def load_module():
    spec = importlib.util.spec_from_file_location("install_g_kade_workspace", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GKadeInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.workspace_dir = tempfile.TemporaryDirectory()
        self.home_dir = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self.workspace_dir.name)
        self.home_root = Path(self.home_dir.name)

    def tearDown(self) -> None:
        self.workspace_dir.cleanup()
        self.home_dir.cleanup()

    def test_detect_workspace_root_uses_git_toplevel(self) -> None:
        subprocess.run(["git", "init", self.workspace_dir.name], check=True, capture_output=True, text=True)
        nested = self.workspace_root / "src" / "nested"
        nested.mkdir(parents=True)

        detected = self.module.detect_workspace_root(nested)

        self.assertEqual(detected, self.workspace_root.resolve())

    def test_detect_richer_upstreams_prefers_richer_gstack_candidate(self) -> None:
        richer = self.home_root / ".codex" / "skills" / "gstack"
        richer.mkdir(parents=True, exist_ok=True)
        (richer / "SKILL.md").write_text("rich gstack\n", encoding="utf-8")
        (richer / "qa").mkdir()
        (richer / "review").mkdir()
        (richer / "docs.md").write_text("extra docs\n", encoding="utf-8")

        gkade, gstack = self.module.detect_richer_upstreams(self.workspace_root, self.home_root)

        self.assertIsNone(gkade)
        self.assertIsNotNone(gstack)
        assert gstack is not None
        self.assertEqual(gstack.root, richer.resolve())
        self.assertIn("qa", gstack.markers)

    def test_scaffolds_repo_local_skill_surfaces_and_kade_overlays(self) -> None:
        actions = []
        actions.extend(
            self.module.scaffold_repo_local_skills(
                self.workspace_root,
                gkade_upstream=None,
                gstack_upstream=None,
                force=False,
                dry_run=False,
            )
        )
        actions.extend(
            self.module.scaffold_kade_overlays(
                self.workspace_root,
                self.home_root,
                layer_result_label="packet wrapper only",
                gkade_upstream=None,
                gstack_upstream=None,
                install_home_profile=True,
                force=False,
                dry_run=False,
            )
        )

        self.assertTrue(actions)
        expected_paths = [
            self.workspace_root / ".agents" / "skills" / "g-kade" / "SKILL.md",
            self.workspace_root / ".agents" / "skills" / "gstack" / "SKILL.md",
            self.workspace_root / ".codex" / "skills" / "g-kade" / "SKILL.md",
            self.workspace_root / ".codex" / "skills" / "gstack" / "SKILL.md",
            self.workspace_root / ".claude" / "skills" / "g-kade" / "SKILL.md",
            self.workspace_root / ".claude" / "skills" / "gstack" / "SKILL.md",
            self.workspace_root / "kade" / "AGENTS.md",
            self.workspace_root / "kade" / "KADE.md",
            self.home_root / ".kade" / "HUMAN.md",
        ]

        for path in expected_paths:
            self.assertTrue(path.exists(), path)

        gkade_text = (self.workspace_root / ".agents" / "skills" / "g-kade" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Fastest Successful Install", gkade_text)
        self.assertIn("Roadblocks And Corrections", gkade_text)
        self.assertIn("Wish I Knew Before Install", gkade_text)

    def test_scaffold_kade_overlays_skips_home_profile_when_not_requested(self) -> None:
        actions = self.module.scaffold_kade_overlays(
            self.workspace_root,
            self.home_root,
            layer_result_label="packet wrapper only",
            gkade_upstream=None,
            gstack_upstream=None,
            install_home_profile=False,
            force=False,
            dry_run=False,
        )

        self.assertTrue(actions)
        self.assertTrue((self.workspace_root / "kade" / "AGENTS.md").exists())
        self.assertTrue((self.workspace_root / "kade" / "KADE.md").exists())
        self.assertFalse((self.home_root / ".kade" / "HUMAN.md").exists())


if __name__ == "__main__":
    unittest.main()
