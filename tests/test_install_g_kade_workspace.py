from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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

    def test_g_kade_mode_defaults_to_installing_home_skills(self) -> None:
        args = self.module.argparse.Namespace(install_home_skills=False, skip_home_skills=False)

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_WIKI_INSTALL_HOME_SKILLS", None)
            os.environ.pop("LLM_WIKI_SKIP_HOME_SKILLS", None)
            self.assertTrue(self.module.resolve_g_kade_home_skill_install(args))

    def test_repo_runtime_dependency_prefers_repo_owned_reserved_path(self) -> None:
        runtime_root = self.workspace_root / "deps" / "pk-skills1" / "gstack"
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "SKILL.md").write_text("repo-owned gstack runtime\n", encoding="utf-8")
        (runtime_root / "qa").mkdir()
        (runtime_root / "review").mkdir()
        (runtime_root / "docs.md").write_text("extra docs\n", encoding="utf-8")

        runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "gstack",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )

        self.assertEqual(runtime["status"], "detected")
        self.assertEqual(runtime["root"], runtime_root.resolve())
        self.assertEqual(runtime["detected_path"], "deps/pk-skills1/gstack")
        self.assertIn("qa", runtime["markers"])

    def test_scaffolds_repo_local_skill_surfaces_and_kade_overlays(self) -> None:
        runtime_root = self.workspace_root / "deps" / "pk-skills1" / "gstack" / "g-kade"
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "SKILL.md").write_text("repo-owned g-kade runtime\n", encoding="utf-8")
        (runtime_root / "kade").mkdir()
        (runtime_root / "review").mkdir()
        (runtime_root / "runtime-notes.md").write_text("notes\n", encoding="utf-8")
        gkade_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "g-kade",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
        )
        gstack_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "gstack",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )
        actions = []
        actions.extend(
            self.module.scaffold_repo_local_skills(
                self.workspace_root,
                gkade_runtime=gkade_runtime,
                gstack_runtime=gstack_runtime,
                force=False,
                dry_run=False,
            )
        )
        actions.extend(
            self.module.scaffold_kade_overlays(
                self.workspace_root,
                self.home_root,
                layer_result_label="packet wrappers plus repo-owned g-kade runtime",
                gkade_runtime=gkade_runtime,
                gstack_runtime=gstack_runtime,
                install_home_profile=True,
                force=False,
                dry_run=False,
            )
        )

        self.assertTrue(actions)
        expected_paths = [
            self.workspace_root / ".agents" / "skills" / "kade-hq" / "SKILL.md",
            self.workspace_root / ".agents" / "skills" / "g-kade" / "SKILL.md",
            self.workspace_root / ".agents" / "skills" / "gstack" / "SKILL.md",
            self.workspace_root / ".codex" / "skills" / "kade-hq" / "SKILL.md",
            self.workspace_root / ".codex" / "skills" / "g-kade" / "SKILL.md",
            self.workspace_root / ".codex" / "skills" / "gstack" / "SKILL.md",
            self.workspace_root / ".claude" / "skills" / "kade-hq" / "SKILL.md",
            self.workspace_root / ".claude" / "skills" / "g-kade" / "SKILL.md",
            self.workspace_root / ".claude" / "skills" / "gstack" / "SKILL.md",
            self.workspace_root / "kade" / "AGENTS.md",
            self.workspace_root / "kade" / "KADE.md",
            self.home_root / ".kade" / "HUMAN.md",
        ]

        for path in expected_paths:
            self.assertTrue(path.exists(), path)

        gkade_text = (self.workspace_root / ".agents" / "skills" / "g-kade" / "SKILL.md").read_text(encoding="utf-8")
        kadehq_text = (self.workspace_root / ".agents" / "skills" / "kade-hq" / "SKILL.md").read_text(encoding="utf-8")
        human_text = (self.home_root / ".kade" / "HUMAN.md").read_text(encoding="utf-8")
        self.assertIn("g-kade is only the unifier skill", kadehq_text)
        self.assertIn("Fastest Successful Install", gkade_text)
        self.assertIn("Roadblocks And Corrections", gkade_text)
        self.assertIn("Wish I Knew Before Install", gkade_text)
        self.assertIn("Repo Runtime Dependency", gkade_text)
        self.assertIn("deps/pk-skills1/gstack/g-kade", gkade_text)
        self.assertIn("detected", gkade_text)
        self.assertIn("How to Work with Kade", human_text)
        self.assertNotIn("This is the global KADE human profile.", human_text)

    def test_scaffold_kade_overlays_preserves_existing_home_profile(self) -> None:
        custom_human = self.home_root / ".kade" / "HUMAN.md"
        custom_human.parent.mkdir(parents=True, exist_ok=True)
        custom_human.write_text("# HUMAN.md\n\nCustom profile\n", encoding="utf-8")
        gkade_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "g-kade",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
        )
        gstack_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "gstack",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )

        actions = self.module.scaffold_kade_overlays(
            self.workspace_root,
            self.home_root,
            layer_result_label="packet wrappers only (repo runtimes missing)",
            gkade_runtime=gkade_runtime,
            gstack_runtime=gstack_runtime,
            install_home_profile=True,
            force=False,
            dry_run=False,
        )

        self.assertTrue(any("(exists)" in action for action in actions))
        self.assertEqual(custom_human.read_text(encoding="utf-8"), "# HUMAN.md\n\nCustom profile\n")

    def test_scaffold_kade_overlays_upgrades_legacy_stub_profile(self) -> None:
        legacy_human = self.home_root / ".kade" / "HUMAN.md"
        legacy_human.parent.mkdir(parents=True, exist_ok=True)
        legacy_human.write_text(self.module.LEGACY_HUMAN_MD_TEXT, encoding="utf-8")
        gkade_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "g-kade",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
        )
        gstack_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "gstack",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )

        actions = self.module.scaffold_kade_overlays(
            self.workspace_root,
            self.home_root,
            layer_result_label="packet wrappers only (repo runtimes missing)",
            gkade_runtime=gkade_runtime,
            gstack_runtime=gstack_runtime,
            install_home_profile=True,
            force=False,
            dry_run=False,
        )

        upgraded_text = legacy_human.read_text(encoding="utf-8")
        self.assertTrue(any("legacy stub" in action for action in actions))
        self.assertIn("How to Work with Kade", upgraded_text)
        self.assertNotEqual(upgraded_text, self.module.LEGACY_HUMAN_MD_TEXT)

    def test_scaffold_kade_overlays_fails_when_packaged_profile_is_missing(self) -> None:
        gkade_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "g-kade",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
        )
        gstack_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "gstack",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )

        with mock.patch.object(self.module, "HUMAN_MD_SOURCE_CANDIDATES", ()):
            with self.assertRaises(FileNotFoundError):
                self.module.scaffold_kade_overlays(
                    self.workspace_root,
                    self.home_root,
                    layer_result_label="packet wrappers only (repo runtimes missing)",
                    gkade_runtime=gkade_runtime,
                    gstack_runtime=gstack_runtime,
                    install_home_profile=True,
                    force=False,
                    dry_run=False,
                )

    def test_scaffold_kade_overlays_skips_home_profile_when_not_requested(self) -> None:
        gkade_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "g-kade",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
        )
        gstack_runtime = self.module.repo_runtime_dependency(
            self.workspace_root,
            "gstack",
            self.module.PACKET.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )
        actions = self.module.scaffold_kade_overlays(
            self.workspace_root,
            self.home_root,
            layer_result_label="packet wrappers only (repo runtimes missing)",
            gkade_runtime=gkade_runtime,
            gstack_runtime=gstack_runtime,
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
