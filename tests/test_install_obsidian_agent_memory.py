from __future__ import annotations

import argparse
import importlib.util
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "installers" / "install_obsidian_agent_memory.py"


def load_module():
    spec = importlib.util.spec_from_file_location("install_obsidian_agent_memory", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class InstallerHomeSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.home_root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_install_home_skills_copies_packet_owned_skill_payloads(self) -> None:
        actions = self.module.install_home_skills(self.home_root, force=False, dry_run=False)

        self.assertTrue(actions)

        expected_paths = [
            self.home_root / ".agents" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".agents" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".agents" / "skills" / "gstack" / "agents" / "openai.yaml",
            self.home_root / ".agents" / "skills" / "g-kade" / "agents" / "openai.yaml",
        ]

        for path in expected_paths:
            self.assertTrue(path.exists(), path)

        marker = self.home_root / ".agents" / "skills" / "gstack" / ".llm-wiki-packet-owner.json"
        self.assertTrue(marker.exists(), marker)

        gstack_text = (self.home_root / ".codex" / "skills" / "gstack" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("packet-owned home-skill wrapper", gstack_text)

        gkade_text = (self.home_root / ".claude" / "skills" / "g-kade" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("packet-owned bridge skill", gkade_text)

    def test_install_home_skills_preserves_richer_existing_skill(self) -> None:
        rich_root = self.home_root / ".claude" / "skills" / "gstack"
        rich_root.mkdir(parents=True, exist_ok=True)
        (rich_root / "SKILL.md").write_text("original richer skill\n", encoding="utf-8")
        (rich_root / "qa").mkdir(parents=True, exist_ok=True)
        (rich_root / "qa" / "SKILL.md").write_text("upstream subskill\n", encoding="utf-8")

        actions = self.module.install_home_skills(self.home_root, force=True, dry_run=False)

        self.assertIn("existing richer skill", "\n".join(actions))
        self.assertEqual((rich_root / "SKILL.md").read_text(encoding="utf-8"), "original richer skill\n")
        self.assertFalse((rich_root / "agents" / "openai.yaml").exists())

    def test_install_home_skills_skips_existing_unowned_skill_even_with_force(self) -> None:
        existing_root = self.home_root / ".agents" / "skills" / "g-kade"
        existing_root.mkdir(parents=True, exist_ok=True)
        (existing_root / "SKILL.md").write_text("existing custom wrapper\n", encoding="utf-8")

        actions = self.module.install_home_skills(self.home_root, force=True, dry_run=False)

        self.assertIn("existing unowned skill root", "\n".join(actions))
        self.assertEqual((existing_root / "SKILL.md").read_text(encoding="utf-8"), "existing custom wrapper\n")
        self.assertFalse((existing_root / ".llm-wiki-packet-owner.json").exists())

    def test_resolve_home_skill_install_defaults_to_disabled(self) -> None:
        args = argparse.Namespace(install_home_skills=False, skip_home_skills=False)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_WIKI_INSTALL_HOME_SKILLS", None)
            os.environ.pop("LLM_WIKI_SKIP_HOME_SKILLS", None)
            self.assertFalse(self.module.resolve_home_skill_install(args))

    def test_ensure_safe_install_root_rejects_home_root(self) -> None:
        with self.assertRaises(SystemExit):
            self.module.ensure_safe_install_root(self.home_root, self.home_root, allow_home_root=False)

    def test_ensure_safe_install_root_allows_explicit_home_root_override(self) -> None:
        self.module.ensure_safe_install_root(self.home_root, self.home_root, allow_home_root=True)


if __name__ == "__main__":
    unittest.main()
