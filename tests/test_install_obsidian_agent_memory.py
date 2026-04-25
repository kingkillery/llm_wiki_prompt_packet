from __future__ import annotations

import argparse
import importlib.util
import json
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
            self.home_root / ".agents" / "skills" / "llm-wiki-skills" / "SKILL.md",
            self.home_root / ".agents" / "skills" / "pokemon-benchmark" / "SKILL.md",
            self.home_root / ".pi" / "agent" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".pi" / "agent" / "skills" / "kade-hq" / "SKILL.md",
            self.home_root / ".pi" / "agent" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".pi" / "agent" / "skills" / "llm-wiki-skills" / "SKILL.md",
            self.home_root / ".pi" / "agent" / "skills" / "pokemon-benchmark" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "kade-hq" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "llm-wiki-skills" / "SKILL.md",
            self.home_root / ".codex" / "skills" / "pokemon-benchmark" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "gstack" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "kade-hq" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "g-kade" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "llm-wiki-skills" / "SKILL.md",
            self.home_root / ".claude" / "skills" / "pokemon-benchmark" / "SKILL.md",
            self.home_root / ".agents" / "skills" / "gstack" / "agents" / "openai.yaml",
            self.home_root / ".agents" / "skills" / "kade-hq" / "agents" / "openai.yaml",
            self.home_root / ".agents" / "skills" / "g-kade" / "agents" / "openai.yaml",
            self.home_root / ".agents" / "skills" / "llm-wiki-skills" / "agents" / "openai.yaml",
            self.home_root / ".agents" / "skills" / "pokemon-benchmark" / "agents" / "openai.yaml",
            self.home_root / ".pi" / "agent" / "skills" / "gstack" / "agents" / "openai.yaml",
            self.home_root / ".pi" / "agent" / "skills" / "kade-hq" / "agents" / "openai.yaml",
            self.home_root / ".pi" / "agent" / "skills" / "g-kade" / "agents" / "openai.yaml",
            self.home_root / ".pi" / "agent" / "skills" / "llm-wiki-skills" / "agents" / "openai.yaml",
            self.home_root / ".pi" / "agent" / "skills" / "pokemon-benchmark" / "agents" / "openai.yaml",
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
        benchmark_text = (self.home_root / ".codex" / "skills" / "pokemon-benchmark" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("run_pokemon_benchmark.ps1", benchmark_text)
        self.assertIn("not itself the harness under test", benchmark_text)
        skill_lifecycle_text = (self.home_root / ".codex" / "skills" / "llm-wiki-skills" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("full tool lifecycle", skill_lifecycle_text)
        self.assertIn("skill_pipeline_run", skill_lifecycle_text)
        self.assertIn("skill_frontier", skill_lifecycle_text)

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
            qmd_repo_ref=self.module.DEFAULT_QMD_REPO_REF,
            qmd_source_checkout=str(self.home_root / "pk-qmd-main"),
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
        self.assertEqual(config["toolset"]["cli"]["python"], "scripts/llm_wiki_packet.py")
        self.assertEqual(config["toolset"]["cli"]["powershell"], "scripts/llm_wiki_packet.ps1")
        self.assertEqual(config["toolset"]["preferred_project_bootstrap_command"], "init")
        self.assertIn("context", config["toolset"]["preferred_project_runtime_commands"])
        self.assertIn("evidence", config["toolset"]["preferred_project_runtime_commands"])
        self.assertIn("improve", config["toolset"]["preferred_project_runtime_commands"])
        self.assertEqual(config["stack"]["retrieval_planner"]["default_evidence_plane"], "all")
        self.assertEqual(config["stack"]["retrieval_planner"]["planes"], ["source", "skills", "preference", "graph", "local"])
        self.assertFalse(config["stack"]["retrieval_planner"]["hf_enabled"])
        self.assertEqual(config["stack"]["retrieval_planner"]["hf_embedding_model"], "BAAI/bge-m3")
        self.assertEqual(
            config["stack"]["retrieval_planner"]["hf_reranker_model"],
            "cross-encoder-testing/reranker-bert-tiny-gooaq-bce",
        )
        self.assertEqual(config["docs"]["contract_path"], "SYSTEM_CONTRACT.md")
        self.assertEqual(config["memory_base"]["name"], "kade-hq")
        self.assertEqual(config["memory_base"]["vault_id"], "fd8411f00d3a9d21")
        self.assertEqual(config["obsidian"]["mcp_server_key"], "obsidian")
        self.assertEqual(config["obsidian"]["package_name"], "@bitbonsai/mcpvault")
        self.assertEqual(config["obsidian"]["wrapper_script_path"], "scripts/llm_wiki_obsidian_mcp.py")
        self.assertIn("mcpvault", "\n".join(config["obsidian"]["local_command_candidates"]))
        self.assertEqual(config["agent_runtimes"]["packet_wrappers"]["kade-hq"]["status"], "home-install-enabled")
        self.assertEqual(config["agent_runtimes"]["packet_wrappers"]["g-kade"]["status"], "home-install-enabled")
        self.assertEqual(config["agent_runtimes"]["packet_wrappers"]["llm-wiki-skills"]["status"], "home-install-enabled")
        self.assertEqual(config["agent_runtimes"]["repo_dependencies"]["g-kade"]["status"], "detected")
        self.assertEqual(config["agent_runtimes"]["repo_dependencies"]["gstack"]["status"], "present-but-thin")
        self.assertEqual(config["agent_runtimes"]["repo_dependencies"]["gstack"]["detected_path"], "deps/pk-skills1/gstack")
        self.assertEqual(config["pk_qmd"]["collection_name"], "kade-hq")
        self.assertEqual(config["pk_qmd"]["repo_ref"], self.module.DEFAULT_QMD_REPO_REF)
        self.assertEqual(config["pk_qmd"]["source_checkout_path"], "pk-qmd-main")
        self.assertEqual(config["pk_qmd"]["config_dir"], ".llm-wiki/qmd-config")
        self.assertIn("pk-qmd", "\n".join(config["pk_qmd"]["local_command_candidates"]))
        self.assertIn("brv", "\n".join(config["byterover"]["local_command_candidates"]))
        self.assertEqual(config["gitvizz"]["repo_url"], "https://github.com/example/gitvizz.git")
        self.assertEqual(config["gitvizz"]["checkout_path"], "deps/gitvizz")
        self.assertEqual(config["gitvizz"]["authorization_env"], "LLM_WIKI_GITVIZZ_AUTHORIZATION")
        self.assertEqual(config["gitvizz"]["auth_token_env"], "LLM_WIKI_GITVIZZ_TOKEN")
        self.assertEqual(config["skills"]["failure_collector_script_path"], "scripts/llm_wiki_failure_collector.py")
        self.assertEqual(config["skills"]["failure_hook_script_path"], "scripts/llm_wiki_failure_hook.py")
        self.assertEqual(config["skills"]["pipeline"]["proposal_dir"], ".llm-wiki/skill-pipeline/proposals")
        self.assertEqual(config["skills"]["pipeline"]["surrogate_review_dir"], ".llm-wiki/skill-pipeline/surrogate-reviews")
        self.assertEqual(config["skills"]["pipeline"]["evolution_run_dir"], ".llm-wiki/skill-pipeline/evolution-runs")
        self.assertEqual(config["skills"]["pipeline"]["frontier_path"], ".llm-wiki/skill-pipeline/frontier.json")
        self.assertEqual(config["skills"]["pipeline"]["failure_event_dir"], ".llm-wiki/skill-pipeline/failures/events")
        self.assertEqual(config["skills"]["pipeline"]["failure_cluster_dir"], ".llm-wiki/skill-pipeline/failures/clusters")
        self.assertEqual(config["skills"]["pipeline"]["failure_benchmark_dir"], ".llm-wiki/skill-pipeline/failures/benchmarks")
        self.assertEqual(config["skills"]["pipeline"]["failure_promotion_threshold"], 3)
        self.assertEqual(config["agent_failure_capture"]["script_path"], "scripts/llm_wiki_agent_failure_capture.py")
        self.assertEqual(config["agent_failure_capture"]["launcher_paths"]["powershell"], "scripts/run_llm_wiki_agent.ps1")
        self.assertIn("pi", config["agent_failure_capture"]["wrapper_supported_agents"])
        self.assertEqual(config["agent_failure_capture"]["commands"]["droid"], "droid")
        self.assertEqual(config["skills"]["pipeline"]["run_dir"], ".llm-wiki/skill-pipeline/runs")

    def test_bootstrap_gitignore_excludes_run_artifacts(self) -> None:
        gitignore = self.module.BOOTSTRAP_FILES[".llm-wiki/.gitignore"]

        self.assertIn("skill-pipeline/runs/*", gitignore)
        self.assertIn("!skill-pipeline/runs/.gitkeep", gitignore)

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
            qmd_source_checkout=str(self.home_root / "pk-qmd-main"),
        )

        report = "\n".join(lines)
        self.assertIn("preflight install-scope: local", report)
        self.assertIn("preflight g-kade wrapper: available", report)
        self.assertIn("preflight g-kade runtime: missing", report)
        self.assertIn("deps/pk-skills1/gstack/g-kade", report)
        self.assertIn("preflight pk-qmd source checkout:", report)
        self.assertIn("pk-qmd-main", report)

    def test_build_stack_dependency_manifest_tracks_brv_for_managed_local_installs(self) -> None:
        manifest = self.module.build_stack_dependency_manifest(
            argparse.Namespace(
                qmd_repo_url="https://github.com/kingkillery/pk-qmd",
                qmd_repo_ref=self.module.DEFAULT_QMD_REPO_REF,
            )
        )

        self.assertEqual(manifest["name"], "llm-wiki-memory-local-tools")
        self.assertEqual(
            manifest["dependencies"]["@kingkillery/pk-qmd"],
            f"git+https://github.com/kingkillery/pk-qmd.git#{self.module.DEFAULT_QMD_REPO_REF}",
        )
        self.assertEqual(manifest["dependencies"]["byterover-cli"], "^3.3.0")
        self.assertEqual(manifest["dependencies"]["@bitbonsai/mcpvault"], "^0.11.0")

    def test_normalize_targets_accepts_pi(self) -> None:
        targets = self.module.normalize_targets("claude,pi,codex")

        self.assertEqual(targets, ["claude", "codex", "pi"])

    def test_ensure_agents_guidance_merges_existing_project_agents_file(self) -> None:
        vault = self.home_root / "vault"
        vault.mkdir(parents=True, exist_ok=True)
        agents_path = vault / "AGENTS.md"
        agents_path.write_text("# Project Agents\n\n## Done when\n\nKeep project rule.\n", encoding="utf-8")

        action = self.module.ensure_agents_guidance(vault, dry_run=False)

        text = agents_path.read_text(encoding="utf-8")
        self.assertIn("merged KADE/memory/retrieval guidance", action)
        self.assertIn("# Project Agents", text)
        self.assertIn("## KADE-HQ, Memory, and Retrieval Routing", text)
        self.assertIn("Use `pk-qmd` first", text)
        self.assertIn("evidence --plane source", text)
        self.assertIn("Treat `g-kade` as the bridge/router", text)
        self.assertIn("## Done when", text)
        self.assertIn("Keep project rule.", text)

        second_action = self.module.ensure_agents_guidance(vault, dry_run=False)
        self.assertIn("AGENTS guidance current", second_action)
        self.assertEqual(1, agents_path.read_text(encoding="utf-8").count("## KADE-HQ, Memory, and Retrieval Routing"))

    def test_install_packet_workspace_inits_then_preserves_existing_vault_state(self) -> None:
        vault = self.home_root / "vault"
        vault.mkdir(parents=True, exist_ok=True)
        home_root = self.home_root / "home"

        args = argparse.Namespace(
            vault=str(vault),
            home_root=str(home_root),
            install_home_skills=False,
            skip_home_skills=True,
            install_scope="local",
            gitvizz_frontend_url="http://localhost:3000",
            gitvizz_backend_url="http://localhost:8003",
            qmd_mcp_url="http://localhost:8181/mcp",
            qmd_command="pk-qmd",
            qmd_repo_url="https://github.com/kingkillery/pk-qmd",
            qmd_repo_ref=self.module.DEFAULT_QMD_REPO_REF,
            brv_command="brv",
            allow_global_tool_install=False,
            gitvizz_repo_url="https://github.com/example/gitvizz.git",
            gitvizz_checkout_path="deps/gitvizz",
            gitvizz_repo_path="",
            g_kade_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
            gstack_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
            memory_vault_path="",
            memory_vault_name="",
            memory_vault_id="",
        )

        actions = self.module.install_packet_workspace(
            vault,
            ["claude", "pi"],
            home_root,
            force=False,
            dry_run=False,
            skip_home_skills=True,
            args=args,
        )

        for path in self.module.packet_required_paths(vault):
            self.assertTrue(path.exists(), path)

        index_path = vault / "wiki" / "index.md"
        log_path = vault / "wiki" / "log.md"
        config_path = vault / self.module.STACK_CONFIG_PATH

        self.assertEqual(index_path.read_text(encoding="utf-8"), "# Wiki Index\n\n")
        self.assertEqual(log_path.read_text(encoding="utf-8"), "# Wiki Log\n\n")

        config = json.loads(config_path.read_text(encoding="utf-8"))
        expected_memory_path = Path(self.module.default_memory_vault_path(vault)).resolve()
        expected_memory_name = self.module.default_memory_vault_name(expected_memory_path)
        self.assertEqual(config["memory_base"]["vault_path"], str(expected_memory_path))
        self.assertEqual(config["memory_base"]["name"], expected_memory_name)
        self.assertEqual(config["obsidian"]["vault_path"], str(expected_memory_path))
        agents_text = (vault / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## KADE-HQ, Memory, and Retrieval Routing", agents_text)
        self.assertIn("Use Obsidian MCP tools", agents_text)
        self.assertTrue(any("Packet-owned home skill install skipped" in action for action in actions))
        self.assertTrue(any("pi target uses root AGENTS.md" in action for action in actions))

        preserved_text = "# Custom Index\n\nKeep this content.\n"
        index_path.write_text(preserved_text, encoding="utf-8")

        second_actions = self.module.install_packet_workspace(
            vault,
            ["claude", "pi"],
            home_root,
            force=False,
            dry_run=False,
            skip_home_skills=True,
            args=args,
        )

        self.assertEqual(index_path.read_text(encoding="utf-8"), preserved_text)
        self.assertTrue(any(str(index_path) in action and "(exists)" in action for action in second_actions))
        self.assertTrue(any(str(config_path) in action and "(config current)" in action for action in second_actions))

    def test_stack_config_refreshes_managed_defaults_and_preserves_project_values(self) -> None:
        vault = self.home_root / "vault"
        vault.mkdir(parents=True, exist_ok=True)
        config_path = vault / self.module.STACK_CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "project_local": {"keep": True},
                    "toolset": {"preferred_project_runtime_commands": ["setup"]},
                    "stack": {"retrieval_planner": {"default_evidence_plane": "local"}},
                    "skills": {"pipeline": {"custom_dir": ".custom"}},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        args = argparse.Namespace(
            vault=str(vault),
            home_root=str(self.home_root / "home"),
            install_home_skills=False,
            skip_home_skills=True,
            install_scope="local",
            gitvizz_frontend_url="http://localhost:3000",
            gitvizz_backend_url="http://localhost:8003",
            qmd_mcp_url="http://localhost:8181/mcp",
            qmd_command="pk-qmd",
            qmd_repo_url="https://github.com/kingkillery/pk-qmd",
            qmd_repo_ref=self.module.DEFAULT_QMD_REPO_REF,
            qmd_source_checkout="",
            brv_command="brv",
            allow_global_tool_install=False,
            gitvizz_repo_url="https://github.com/example/gitvizz.git",
            gitvizz_checkout_path="deps/gitvizz",
            gitvizz_repo_path="",
            g_kade_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["g-kade"],
            gstack_dependency_path=self.module.REPO_RUNTIME_DEFAULT_PATHS["gstack"],
            memory_vault_path="",
            memory_vault_name="",
            memory_vault_id="",
        )

        actions = self.module.install_packet_workspace(
            vault,
            ["codex"],
            self.home_root / "home",
            force=False,
            dry_run=False,
            skip_home_skills=True,
            args=args,
        )

        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertTrue(config["project_local"]["keep"])
        self.assertEqual(config["skills"]["pipeline"]["custom_dir"], ".custom")
        self.assertIn("evidence", config["toolset"]["preferred_project_runtime_commands"])
        self.assertEqual(config["stack"]["retrieval_planner"]["default_evidence_plane"], "all")
        self.assertEqual(config["skills"]["pipeline"]["run_dir"], ".llm-wiki/skill-pipeline/runs")
        self.assertTrue(any(str(config_path) in action and action.startswith("update") for action in actions))


if __name__ == "__main__":
    unittest.main()
