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
            self.home_root / ".agents" / "skills" / "kade-hq" / "SKILL.md",
            self.home_root / ".agents" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "kade-hq" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "kade-hq" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".agents" / "skills" / "gstack" / "agents" / "openai.yaml",
            self.home_root / ".agents" / "skills" / "kade-hq" / "agents" / "openai.yaml",
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
        kadehq_text = (self.home_root / ".agents" / "skills" / "kade-hq" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("bridge skill that coordinates", kadehq_text)

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

    def test_repo_runtime_dependency_status_defaults_to_missing_reserved_path(self) -> None:
        status = self.module.repo_runtime_dependency_status(
            self.home_root,
            "g-kade",
            self.module.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
        )

        self.assertEqual(status["status"], "missing")
        self.assertEqual(status["configured_path"], self.module.REPO_RUNTIME_DEFAULT_PATHS["g-kade"])
        self.assertIsNone(status["detected_path"])

    def test_repo_runtime_dependency_status_detects_repo_owned_richer_runtime(self) -> None:
        runtime_root = self.home_root / "deps" / "pk-skills1" / "gstack"
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "SKILL.md").write_text("repo-owned gstack runtime\n", encoding="utf-8")
        (runtime_root / "qa").mkdir()
        (runtime_root / "review").mkdir()
        (runtime_root / "docs.md").write_text("runtime docs\n", encoding="utf-8")

        status = self.module.repo_runtime_dependency_status(
            self.home_root,
            "gstack",
            self.module.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )

        self.assertEqual(status["status"], "detected")
        self.assertEqual(status["detected_path"], "deps/pk-skills1/gstack")
        self.assertIn("qa", status["markers"])

    def test_build_stack_config_records_wrapper_and_repo_runtime_status(self) -> None:
        runtime_root = self.home_root / "deps" / "pk-skills1" / "gstack" / "g-kade"
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "SKILL.md").write_text("repo-owned g-kade runtime\n", encoding="utf-8")
        (runtime_root / "kade").mkdir()
        (runtime_root / "review").mkdir()
        (runtime_root / "notes.md").write_text("runtime notes\n", encoding="utf-8")

        args = argparse.Namespace(
            vault=str(self.home_root),
            home_root=str(self.home_root / "home"),
            install_home_skills=True,
            skip_home_skills=False,
            install_scope="global",
            gitvizz_frontend_url="http://localhost:3000",
            gitvizz_backend_url="http://localhost:8003",
            qmd_mcp_url="http://localhost:8181/mcp",
            qmd_command="pk-qmd",
            qmd_repo_url="https://github.com/kingkillery/pk-qmd",
            brv_command="brv",
            allow_global_tool_install=False,
            gitvizz_repo_url="https://github.com/example/gitvizz.git",
            gitvizz_checkout_path="deps/gitvizz",
            gitvizz_repo_path="",
            g_kade_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
            gstack_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
            memory_vault_path=str(self.home_root / "memory-vault"),
            memory_vault_name="kade-hq",
            memory_vault_id="fd8411f00d3a9d21",
        )

        config = self.module.build_stack_config(args)

        self.assertEqual(config["tooling"]["install_scope"], "global")
        self.assertEqual(config["memory_base"]["name"], "kade-hq")
        self.assertEqual(config["memory_base"]["vault_id"], "fd8411f00d3a9d21")
        self.assertEqual(config["agent_runtimes"]["packet_wrappers"]["g-kade"]["status"], "home-install-enabled")
        self.assertEqual(config["agent_runtimes"]["repo_dependencies"]["g-kade"]["status"], "detected")
        self.assertEqual(config["agent_runtimes"]["repo_dependencies"]["gstack"]["status"], "present-but-thin")
        self.assertEqual(config["agent_runtimes"]["repo_dependencies"]["gstack"]["detected_path"], "deps/pk-skills1/gstack")
        self.assertEqual(config["pk_qmd"]["collection_name"], "kade-hq")
        self.assertIn("pk-qmd", "\n".join(config["pk_qmd"]["local_command_candidates"]))
        self.assertIn("brv", "\n".join(config["byterover"]["local_command_candidates"]))
        self.assertEqual(config["gitvizz"]["repo_url"], "https://github.com/example/gitvizz.git")
        self.assertEqual(config["gitvizz"]["checkout_path"], "deps/gitvizz")

    def test_build_preflight_report_mentions_repo_runtime_contract(self) -> None:
        lines = self.module.build_preflight_report(
            self.home_root,
            self.home_root / "home",
            install_home_skills=False,
            run_setup=False,
            allow_global_tool_install=False,
            install_scope="local",
            g_kade_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
            gstack_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
        )

        report = "\n".join(lines)
        self.assertIn("preflight install-scope: local", report)
        self.assertIn("preflight g-kade wrapper: available", report)
        self.assertIn("preflight g-kade runtime: missing", report)
        self.assertIn("deps/pk-skills1/gstack/g-kade", report)

    def test_build_stack_dependency_manifest_tracks_brv_for_managed_local_installs(self) -> None:
        manifest = self.module.build_stack_dependency_manifest(argparse.Namespace())

        self.assertEqual(manifest["name"], "llm-wiki-memory-local-tools")
        self.assertEqual(manifest["dependencies"]["byterover-cli"], "^3.3.0")


if __name__ == "__main__":
    unittest.main()
