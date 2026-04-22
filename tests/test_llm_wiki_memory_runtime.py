from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_memory_runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_memory_runtime", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        (self.workspace / ".llm-wiki").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_config(self, payload: dict[str, object]) -> Path:
        config_path = self.workspace / ".llm-wiki" / "config.json"
        config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return config_path

    def test_qmd_package_spec_includes_pinned_ref(self) -> None:
        spec = self.module.qmd_package_spec(
            {"qmd_repo_url": "https://github.com/kingkillery/pk-qmd", "qmd_repo_ref": "abc123"}
        )
        self.assertEqual(spec, "git+https://github.com/kingkillery/pk-qmd.git#abc123")

    def test_write_qmd_wrappers_creates_shell_powerShell_and_cmd_surfaces(self) -> None:
        managed_root = self.workspace / ".llm-wiki" / "tools"
        dist_path = self.workspace / "deps" / "pk-qmd" / "dist" / "cli" / "qmd.js"
        dist_path.parent.mkdir(parents=True, exist_ok=True)
        dist_path.write_text("console.log('ok')\n", encoding="utf-8")

        wrappers = self.module.write_qmd_wrappers(managed_root, dist_path)

        self.assertEqual(len(wrappers), 4)
        self.assertTrue((managed_root / "bin" / "pk-qmd.cmd").exists())
        self.assertTrue((managed_root / "bin" / "pk-qmd.ps1").exists())
        self.assertTrue((managed_root / "bin" / "pk-qmd").exists())

    def test_resolve_shell_command_keeps_cmd_entrypoint_as_direct_executable(self) -> None:
        cmd_path = self.workspace / "Program Files" / "nodejs" / "npm.cmd"
        cmd_path.parent.mkdir(parents=True, exist_ok=True)
        cmd_path.write_text("@echo off\r\n", encoding="ascii")

        invocation = self.module.resolve_shell_command(cmd_path)

        self.assertEqual(invocation, [str(cmd_path)])

    def test_update_json_mcp_config_merges_server_without_dropping_existing_entries(self) -> None:
        settings_path = self.workspace / "settings.json"
        settings_path.write_text(
            json.dumps({"mcpServers": {"existing": {"command": "echo", "args": ["ok"]}}}, indent=2),
            encoding="utf-8",
        )

        self.module.update_json_mcp_config(settings_path, "pk-qmd", "pk-qmd", ["mcp"], factory_style=False)

        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertIn("existing", payload["mcpServers"])
        self.assertEqual(payload["mcpServers"]["pk-qmd"]["args"], ["mcp"])

    def test_update_json_mcp_config_preserves_existing_obsidian_server_when_patching_runtime(self) -> None:
        settings_path = self.workspace / "settings.json"
        obsidian_payload = {
            "command": "npx",
            "args": ["-y", "@bitbonsai/mcpvault", r"C:\Vaults\Kade-HQ"],
            "env": {"OBSIDIAN_VAULT_PATH": r"C:\Vaults\Kade-HQ"},
        }
        settings_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "obsidian": obsidian_payload,
                        "qmd": {"command": "old-qmd", "args": ["mcp"]},
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        self.module.update_json_mcp_config(settings_path, "pk-qmd", "pk-qmd", ["mcp"], factory_style=False)
        self.module.update_json_mcp_config(
            settings_path,
            "llm-wiki-skills",
            "python",
            ["scripts/llm_wiki_skill_mcp.py", "--workspace", ".", "mcp"],
            factory_style=False,
        )

        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["mcpServers"]["obsidian"], obsidian_payload)
        self.assertEqual(payload["mcpServers"]["pk-qmd"]["args"], ["mcp"])
        self.assertEqual(payload["mcpServers"]["llm-wiki-skills"]["command"], "python")
        self.assertNotIn("qmd", payload["mcpServers"])

    def test_patch_hf_mcp_configs_skips_when_hf_token_missing(self) -> None:
        summary: list[str] = []

        with mock.patch.dict(self.module.os.environ, {}, clear=True):
            self.module.patch_hf_mcp_configs(summary)

        self.assertEqual(summary, ["Skipped Hugging Face MCP wiring (HF_TOKEN not set)"])
        self.assertFalse((self.workspace / ".claude" / "settings.json").exists())
        self.assertFalse((self.workspace / ".factory" / "mcp.json").exists())

    def test_patch_hf_mcp_configs_wires_claude_and_factory_without_persisting_token(self) -> None:
        summary: list[str] = []

        with mock.patch.dict(self.module.os.environ, {"HF_TOKEN": "hf_test_secret"}, clear=True):
            with mock.patch.object(self.module.Path, "home", return_value=self.workspace):
                self.module.patch_hf_mcp_configs(summary)

        claude_payload = json.loads((self.workspace / ".claude" / "settings.json").read_text(encoding="utf-8"))
        factory_payload = json.loads((self.workspace / ".factory" / "mcp.json").read_text(encoding="utf-8"))

        expected_args = [
            "-y",
            "mcp-remote@0.1.38",
            "https://huggingface.co/mcp",
            "--header",
            "Authorization:${HF_AUTH_HEADER}",
        ]
        expected_env = {"HF_AUTH_HEADER": "Bearer ${HF_TOKEN}"}

        self.assertEqual(claude_payload["mcpServers"]["huggingface"]["command"], "npx")
        self.assertEqual(claude_payload["mcpServers"]["huggingface"]["args"], expected_args)
        self.assertEqual(claude_payload["mcpServers"]["huggingface"]["env"], expected_env)

        self.assertEqual(factory_payload["mcpServers"]["huggingface"]["type"], "stdio")
        self.assertEqual(factory_payload["mcpServers"]["huggingface"]["command"], "npx")
        self.assertEqual(factory_payload["mcpServers"]["huggingface"]["args"], expected_args)
        self.assertEqual(factory_payload["mcpServers"]["huggingface"]["env"], expected_env)
        self.assertFalse((self.workspace / ".codex" / "config.toml").exists())

        self.assertIn("Updated ~/.claude/settings.json for huggingface", summary)
        self.assertIn("Updated ~/.factory/mcp.json for huggingface", summary)
        self.assertTrue(any("Skipped ~/.codex/config.toml for huggingface" in item for item in summary))
        self.assertNotIn("hf_test_secret", json.dumps(claude_payload))
        self.assertNotIn("hf_test_secret", json.dumps(factory_payload))

    def test_workspace_mcp_json_declares_obsidian_plus_required_servers(self) -> None:
        mcp_path = REPO_ROOT / ".mcp.json"

        payload = json.loads(mcp_path.read_text(encoding="utf-8"))

        self.assertEqual(set(payload.keys()), {"pk-qmd", "llm-wiki-skills", "obsidian", "brv"})
        self.assertEqual(payload["pk-qmd"]["args"], ["mcp"])
        self.assertEqual(payload["llm-wiki-skills"]["command"], "python")
        self.assertEqual(payload["brv"]["args"], ["mcp"])
        self.assertEqual(payload["obsidian"]["command"], "python")
        self.assertIn("support/scripts/llm_wiki_obsidian_mcp.py", payload["obsidian"]["args"])
        self.assertIn("--ensure-install", payload["obsidian"]["args"])
        self.assertIn("OBSIDIAN_VAULT_PATH", payload["obsidian"]["env"])

    def test_update_codex_toml_uses_windows_safe_literal_strings(self) -> None:
        config_path = self.workspace / "config.toml"

        self.module.update_codex_toml(
            config_path,
            "llm-wiki-skills",
            "python",
            [
                r"C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet\support\scripts\llm_wiki_skill_mcp.py",
                "--workspace",
                r"C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet",
                "mcp",
            ],
            env={"OBSIDIAN_VAULT_PATH": r"C:\Vaults\Kade-HQ"},
        )

        content = config_path.read_text(encoding="utf-8")
        self.assertIn("command = 'python'", content)
        self.assertIn(r"'C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet\support\scripts\llm_wiki_skill_mcp.py'", content)
        self.assertIn(r"'C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet'", content)
        self.assertIn(r"env = { OBSIDIAN_VAULT_PATH = 'C:\Vaults\Kade-HQ' }", content)

    def test_build_runtime_uses_configured_paths_and_repo_ref(self) -> None:
        config_path = self.write_config(
            {
                "tooling": {"install_scope": "global", "managed_tool_root": ".llm-wiki/tools"},
                "memory_base": {"name": "kade-hq", "vault_path": str(self.workspace / "memory"), "vault_id": "vault-1"},
                "pk_qmd": {
                    "command": "pk-qmd",
                    "repo_url": "https://github.com/kingkillery/pk-qmd",
                    "repo_ref": "abc123",
                    "checkout_path": ".llm-wiki/tools/pk-qmd",
                    "local_command_candidates": [".llm-wiki/tools/bin/pk-qmd.cmd"],
                    "collection_name": "kade-hq",
                    "context": "ctx",
                    "source_checkout_path": ".llm-wiki/tools/pk-qmd-main",
                    "config_dir": ".llm-wiki/qmd-config",
                    "source_path": str(self.workspace / "memory"),
                },
                "byterover": {
                    "command": "brv",
                    "install_root": ".llm-wiki/tools/brv",
                    "local_command_candidates": [".llm-wiki/tools/brv/node_modules/.bin/brv.cmd"],
                },
                "obsidian": {
                    "mcp_server_key": "obsidian",
                    "package_name": "@bitbonsai/mcpvault",
                    "wrapper_script_path": "scripts/llm_wiki_obsidian_mcp.py",
                    "install_root": ".llm-wiki/tools/obsidian-mcp",
                    "local_command_candidates": [".llm-wiki/tools/obsidian-mcp/node_modules/.bin/mcpvault.cmd"],
                    "vault_path": str(self.workspace / "memory"),
                },
                "gitvizz": {
                    "frontend_url": "http://localhost:3000",
                    "backend_url": "http://localhost:8003",
                    "repo_url": "https://github.com/example/gitvizz.git",
                    "checkout_path": ".llm-wiki/tools/gitvizz",
                },
                "skills": {
                    "mcp_server_key": "llm-wiki-skills",
                    "script_path": "scripts/llm_wiki_skill_mcp.py",
                    "failure_hook_script_path": "scripts/llm_wiki_failure_hook.py",
                    "registry_path": ".llm-wiki/skills-registry.json",
                    "pipeline": {"brief_dir": ".llm-wiki/skill-pipeline/briefs"},
                },
                "agent_failure_capture": {
                    "script_path": "scripts/llm_wiki_agent_failure_capture.py",
                    "launcher_paths": {
                        "powershell": "scripts/run_llm_wiki_agent.ps1",
                        "shell": "scripts/run_llm_wiki_agent.sh",
                        "cmd": "scripts/run_llm_wiki_agent.cmd",
                    },
                    "commands": {
                        "claude": "claude",
                        "codex": "codex",
                        "droid": "droid",
                        "pi": "pi",
                    },
                },
            }
        )

        args = self.module.argparse.Namespace(
            mode="setup",
            workspace=str(self.workspace),
            config_path=str(config_path),
            qmd_source="",
            qmd_source_checkout="",
            qmd_repo_url="",
            qmd_command="",
            qmd_collection="",
            qmd_context="",
            brv_command="",
            obsidian_vault_path="",
            gitvizz_frontend_url="",
            gitvizz_backend_url="",
            gitvizz_repo_url="",
            gitvizz_checkout_path="",
            gitvizz_repo_path="",
            skip_qmd=False,
            skip_mcp=False,
            skip_qmd_bootstrap=False,
            skip_qmd_embed=False,
            skip_brv=False,
            skip_brv_init=False,
            skip_gitvizz=False,
            skip_gitvizz_start=False,
            allow_global_tool_install=False,
            verify_only=False,
        )

        runtime = self.module.build_runtime(args)

        self.assertEqual(runtime["install_scope"], "global")
        self.assertEqual(runtime["qmd_repo_ref"], "abc123")
        self.assertEqual(runtime["memory_base_id"], "vault-1")
        self.assertEqual(runtime["obsidian_server_key"], "obsidian")
        self.assertTrue(str(runtime["qmd_source_checkout"]).endswith(".llm-wiki\\tools\\pk-qmd-main") or str(runtime["qmd_source_checkout"]).endswith(".llm-wiki/tools/pk-qmd-main"))
        self.assertTrue(str(runtime["qmd_config_dir"]).endswith(".llm-wiki\\qmd-config") or str(runtime["qmd_config_dir"]).endswith(".llm-wiki/qmd-config"))
        self.assertEqual(runtime["obsidian_package_name"], "@bitbonsai/mcpvault")
        self.assertTrue(str(runtime["obsidian_install_root"]).endswith(".llm-wiki\\tools\\obsidian-mcp") or str(runtime["obsidian_install_root"]).endswith(".llm-wiki/tools/obsidian-mcp"))
        self.assertTrue(str(runtime["failure_hook_script_path"]).endswith("scripts\\llm_wiki_failure_hook.py") or str(runtime["failure_hook_script_path"]).endswith("scripts/llm_wiki_failure_hook.py"))
        self.assertTrue(str(runtime["agent_failure_capture_script_path"]).endswith("scripts\\llm_wiki_agent_failure_capture.py") or str(runtime["agent_failure_capture_script_path"]).endswith("scripts/llm_wiki_agent_failure_capture.py"))
        self.assertIn("pi", runtime["agent_failure_commands"])
        self.assertTrue(str(runtime["qmd_checkout_path"]).endswith(".llm-wiki\\tools\\pk-qmd") or str(runtime["qmd_checkout_path"]).endswith(".llm-wiki/tools/pk-qmd"))

    def test_qmd_runtime_env_sets_workspace_local_config_dir(self) -> None:
        runtime = {"qmd_config_dir": self.workspace / ".llm-wiki" / "qmd-config"}

        env = self.module.qmd_runtime_env(runtime)

        self.assertEqual(env["QMD_CONFIG_DIR"], str(self.workspace / ".llm-wiki" / "qmd-config"))
        self.assertTrue((self.workspace / ".llm-wiki" / "qmd-config").exists())

    def test_ensure_managed_qmd_prefers_source_checkout_over_managed_candidate(self) -> None:
        source_checkout = self.workspace / "pk-qmd-main"
        source_entrypoint = source_checkout / "dist" / "cli" / "qmd.js"
        source_entrypoint.parent.mkdir(parents=True, exist_ok=True)
        source_entrypoint.write_text("console.log('source')\n", encoding="utf-8")

        managed_candidate = self.workspace / ".llm-wiki" / "tools" / "bin" / "pk-qmd.cmd"
        managed_candidate.parent.mkdir(parents=True, exist_ok=True)
        managed_candidate.write_text("@echo off\r\n", encoding="ascii")

        runtime = {
            "managed_tool_root": self.workspace / ".llm-wiki" / "tools",
            "qmd_checkout_path": self.workspace / ".llm-wiki" / "tools" / "pk-qmd",
            "qmd_local_candidates": [managed_candidate],
            "qmd_source_checkout": source_checkout,
            "qmd_command": "pk-qmd",
            "workspace_root": self.workspace,
            "verify_only": False,
            "allow_global_tool_install": False,
        }
        summary: list[str] = []
        failures: list[str] = []
        state: dict[str, object] = {}

        resolved = self.module.ensure_managed_qmd(runtime, summary, failures, state)

        self.assertEqual(resolved, str(source_entrypoint))
        self.assertIn("resolved preferred source checkout", "\n".join(summary))
        self.assertEqual(failures, [])

    def test_bootstrap_qmd_uses_workspace_local_qmd_config_and_passes_explicit_command_to_runner(self) -> None:
        qmd_command = str(self.workspace / "pk-qmd-main" / "dist" / "cli" / "qmd.js")
        runner = self.workspace / "scripts" / "qmd_embed_runner.mjs"
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text("// runner\n", encoding="utf-8")
        source_path = self.workspace / "memory"
        source_path.mkdir(parents=True, exist_ok=True)

        runtime = {
            "qmd_collection": "kade-hq",
            "qmd_source_path": source_path,
            "qmd_context": "ctx",
            "qmd_config_dir": self.workspace / ".llm-wiki" / "qmd-config",
            "verify_only": False,
            "skip_qmd_embed": False,
            "workspace_root": self.workspace,
        }
        summary: list[str] = []
        failures: list[str] = []
        state: dict[str, object] = {}
        calls: list[tuple[str, list[str], dict[str, str] | None]] = []

        def fake_run(command_name, args, **kwargs):
            calls.append((command_name, args, kwargs.get("env")))
            if command_name == qmd_command and args == ["collection", "list"]:
                return mock.Mock(returncode=0, stdout="", stderr="")
            if command_name == qmd_command and args == ["context", "list"]:
                return mock.Mock(returncode=0, stdout="", stderr="")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(self.module, "qmd_supports_collections", return_value=True):
            with mock.patch.object(self.module, "command_in_path", return_value="node"):
                with mock.patch.object(self.module, "env_flag", return_value=False):
                    with mock.patch.object(self.module, "run_command", side_effect=fake_run):
                        self.module.bootstrap_qmd(runtime, qmd_command, summary, failures, state)

        self.assertEqual(failures, [])
        self.assertTrue((self.workspace / ".llm-wiki" / "qmd-config").exists())
        self.assertIn("Added qmd collection: kade-hq", summary)
        self.assertIn("Added qmd context: qmd://kade-hq/", summary)
        self.assertIn("Ran qmd embed runner", summary)
        node_call = next(call for call in calls if call[0] == "node")
        self.assertIn("--command", node_call[1])
        self.assertIn(qmd_command, node_call[1])
        self.assertEqual(node_call[2]["QMD_CONFIG_DIR"], str(self.workspace / ".llm-wiki" / "qmd-config"))
        qmd_calls = [call for call in calls if call[0] == qmd_command]
        self.assertTrue(all(call[2]["QMD_CONFIG_DIR"] == str(self.workspace / ".llm-wiki" / "qmd-config") for call in qmd_calls))

    def test_build_claude_failure_hook_handler_supports_posix_and_powershell(self) -> None:
        runtime = {
            "workspace_root": self.workspace,
            "failure_hook_script_path": self.workspace / "scripts" / "llm_wiki_failure_hook.py",
        }
        runtime["failure_hook_script_path"].parent.mkdir(parents=True, exist_ok=True)
        runtime["failure_hook_script_path"].write_text("#!/usr/bin/env python3\n", encoding="utf-8")

        posix_handler = self.module.build_claude_failure_hook_handler(
            runtime,
            python_command=["python3"],
            use_powershell=False,
        )
        self.assertEqual(posix_handler["type"], "command")
        self.assertNotIn("shell", posix_handler)
        self.assertIn("$CLAUDE_PROJECT_DIR", posix_handler["command"])
        self.assertIn("llm_wiki_failure_hook.py", posix_handler["command"])

        powershell_handler = self.module.build_claude_failure_hook_handler(
            runtime,
            python_command=["py", "-3"],
            use_powershell=True,
        )
        self.assertEqual(powershell_handler["shell"], "powershell")
        self.assertIn("$env:CLAUDE_PROJECT_DIR", powershell_handler["command"])
        self.assertIn("Join-Path", powershell_handler["command"])
        self.assertIn("llm_wiki_failure_hook.py", powershell_handler["command"])

    def test_run_setup_still_patches_skill_mcp_when_qmd_status_fails(self) -> None:
        runtime = {
            "install_scope": "local",
            "managed_tool_root": self.workspace / ".llm-wiki" / "tools",
            "memory_base_path": self.workspace / "memory",
            "memory_base_id": "",
            "allow_global_tool_install": False,
            "skip_qmd": False,
            "skip_mcp": False,
            "skip_qmd_bootstrap": True,
            "skip_brv": True,
            "skip_gitvizz": True,
            "skip_gitvizz_start": True,
            "workspace_root": self.workspace,
            "verify_only": False,
            "obsidian_server_key": "obsidian",
            "obsidian_package_name": "@bitbonsai/mcpvault",
            "obsidian_install_root": self.workspace / ".llm-wiki" / "tools" / "obsidian-mcp",
            "obsidian_local_candidates": [],
            "obsidian_vault_path": self.workspace / "memory",
            "skill_server_key": "llm-wiki-skills",
            "skill_script_path": self.workspace / "support" / "scripts" / "llm_wiki_skill_mcp.py",
            "agent_failure_capture_script_path": self.workspace / "support" / "scripts" / "llm_wiki_agent_failure_capture.py",
            "agent_failure_launcher_paths": {},
            "agent_failure_commands": {},
        }
        runtime["skill_script_path"].parent.mkdir(parents=True, exist_ok=True)
        runtime["skill_script_path"].write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        runtime["agent_failure_capture_script_path"].parent.mkdir(parents=True, exist_ok=True)
        runtime["agent_failure_capture_script_path"].write_text("#!/usr/bin/env python3\n", encoding="utf-8")

        summary: list[str] = []
        failures: list[str] = []
        state: dict[str, object] = {}

        with mock.patch.object(self.module, "ensure_managed_qmd", return_value="pk-qmd"):
            with mock.patch.object(self.module, "ensure_managed_obsidian", return_value="C:/tools/mcpvault.cmd"):
                with mock.patch.object(
                    self.module,
                    "run_command",
                    return_value=mock.Mock(returncode=1, stdout="", stderr="pk-qmd broke"),
                ):
                    with mock.patch.object(self.module, "patch_mcp_configs") as patch_mcp:
                        with mock.patch.object(self.module, "patch_claude_local_hook_settings"):
                            with mock.patch.object(self.module, "verify_agent_failure_capture"):
                                self.module.run_setup(runtime, summary, failures, state)

        patch_mcp.assert_called_once_with(runtime, "pk-qmd", "C:/tools/mcpvault.cmd", summary)
        self.assertIn("pk-qmd broke", failures)

    def test_ensure_managed_qmd_falls_back_when_existing_command_is_unusable(self) -> None:
        source_root = self.workspace / "deps" / "pk-qmd"
        dist_path = source_root / "dist" / "cli" / "qmd.js"
        dist_path.parent.mkdir(parents=True, exist_ok=True)
        dist_path.write_text("console.log('ok')\n", encoding="utf-8")

        runtime = {
            "managed_tool_root": self.workspace / ".llm-wiki" / "tools",
            "qmd_checkout_path": self.workspace / ".llm-wiki" / "tools" / "pk-qmd",
            "qmd_local_candidates": [],
            "qmd_command": "pk-qmd",
            "workspace_root": self.workspace,
            "qmd_source": source_root,
            "verify_only": False,
            "allow_global_tool_install": False,
            "qmd_repo_url": "https://github.com/kingkillery/pk-qmd",
            "qmd_repo_ref": "abc123",
        }
        summary: list[str] = []
        failures: list[str] = []

        with mock.patch.object(self.module, "command_in_path", return_value="C:/broken/pk-qmd.cmd"):
            with mock.patch.object(
                self.module,
                "probe_command",
                return_value=(False, "The system cannot find the path specified."),
            ):
                resolved = self.module.ensure_managed_qmd(runtime, summary, failures, {})

        self.assertEqual(resolved, str(dist_path))
        self.assertTrue(any("existing command unusable" in line for line in summary))
        self.assertTrue(any("fallback reason" in line for line in summary))
        self.assertFalse(failures)

    def test_ensure_managed_qmd_skips_build_when_dist_already_exists(self) -> None:
        checkout = self.workspace / ".llm-wiki" / "tools" / "pk-qmd"
        dist_path = checkout / "dist" / "cli" / "qmd.js"
        dist_path.parent.mkdir(parents=True, exist_ok=True)
        dist_path.write_text("console.log('ok')\n", encoding="utf-8")
        (checkout / "package.json").write_text(json.dumps({"scripts": {"build": "tsc"}}), encoding="utf-8")

        runtime = {
            "managed_tool_root": self.workspace / ".llm-wiki" / "tools",
            "qmd_checkout_path": checkout,
            "qmd_local_candidates": [],
            "qmd_command": "pk-qmd",
            "workspace_root": self.workspace,
            "qmd_source": None,
            "verify_only": False,
            "allow_global_tool_install": False,
            "qmd_repo_url": "https://github.com/kingkillery/pk-qmd",
            "qmd_repo_ref": "abc123",
        }
        summary: list[str] = []
        failures: list[str] = []

        def fake_run(command_name, args, **kwargs):
            if args[:2] == ["-C", str(checkout)] and "checkout" in args:
                return mock.Mock(returncode=0, stdout="", stderr="")
            if args == ["install"]:
                return mock.Mock(returncode=0, stdout="", stderr="")
            raise AssertionError(f"Unexpected command: {command_name} {args}")

        with mock.patch.object(self.module, "command_in_path", return_value=None):
            with mock.patch.object(self.module, "resolve_git_command", return_value="git"):
                with mock.patch.object(self.module, "resolve_npm_command", return_value="npm"):
                    with mock.patch.object(self.module, "run_command", side_effect=fake_run):
                        resolved = self.module.ensure_managed_qmd(runtime, summary, failures, {})

        self.assertTrue(str(resolved).endswith("pk-qmd.cmd") or str(resolved).endswith("pk-qmd"))
        self.assertFalse(any("managed install failed" in failure for failure in failures))

    def test_ensure_managed_qmd_tolerates_build_error_when_dist_exists_afterward(self) -> None:
        checkout = self.workspace / ".llm-wiki" / "tools" / "pk-qmd"
        checkout.mkdir(parents=True, exist_ok=True)
        dist_path = checkout / "dist" / "cli" / "qmd.js"
        (checkout / "package.json").write_text(json.dumps({"scripts": {"build": "tsc"}}), encoding="utf-8")

        runtime = {
            "managed_tool_root": self.workspace / ".llm-wiki" / "tools",
            "qmd_checkout_path": checkout,
            "qmd_local_candidates": [],
            "qmd_command": "pk-qmd",
            "workspace_root": self.workspace,
            "qmd_source": None,
            "verify_only": False,
            "allow_global_tool_install": False,
            "qmd_repo_url": "https://github.com/kingkillery/pk-qmd",
            "qmd_repo_ref": "abc123",
        }
        summary: list[str] = []
        failures: list[str] = []

        def fake_run(command_name, args, **kwargs):
            if args[:2] == ["-C", str(checkout)] and "checkout" in args:
                return mock.Mock(returncode=0, stdout="", stderr="")
            if args == ["install"]:
                dist_path.parent.mkdir(parents=True, exist_ok=True)
                dist_path.write_text("console.log('ok')\n", encoding="utf-8")
                return mock.Mock(returncode=0, stdout="", stderr="")
            if args == ["run", "build"]:
                raise RuntimeError("build failed")
            raise AssertionError(f"Unexpected command: {command_name} {args}")

        with mock.patch.object(self.module, "command_in_path", return_value=None):
            with mock.patch.object(self.module, "resolve_git_command", return_value="git"):
                with mock.patch.object(self.module, "resolve_npm_command", return_value="npm"):
                    with mock.patch.object(self.module, "run_command", side_effect=fake_run):
                        resolved = self.module.ensure_managed_qmd(runtime, summary, failures, {})

        self.assertTrue(str(resolved).endswith("pk-qmd.cmd") or str(resolved).endswith("pk-qmd"))
        self.assertTrue(any("pk-qmd build fallback" in line for line in summary))
        self.assertFalse(failures)

    def test_update_claude_hook_settings_preserves_existing_hooks_and_replaces_managed_entries(self) -> None:
        settings_path = self.workspace / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(
                {
                    "model": "claude-sonnet",
                    "hooks": {
                        "PostToolUseFailure": [
                            {
                                "matcher": "Bash",
                                "hooks": [
                                    {"type": "command", "command": "echo custom"}
                                ],
                            },
                            {
                                "matcher": "*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": 'python scripts/llm_wiki_failure_hook.py --workspace .',
                                    }
                                ],
                            },
                        ]
                    },
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        self.module.update_claude_hook_settings(
            settings_path,
            {
                "PostToolUseFailure": {
                    "type": "command",
                    "command": 'python scripts/llm_wiki_failure_hook.py --workspace .',
                    "timeout": 30,
                },
                "StopFailure": {
                    "type": "command",
                    "command": 'python scripts/llm_wiki_failure_hook.py --workspace .',
                    "timeout": 30,
                },
            },
        )

        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["model"], "claude-sonnet")
        post_groups = payload["hooks"]["PostToolUseFailure"]
        self.assertEqual(len(post_groups), 2)
        self.assertEqual(post_groups[0]["hooks"][0]["command"], "echo custom")
        self.assertEqual(post_groups[1]["matcher"], "*")
        self.assertEqual(post_groups[1]["hooks"][0]["timeout"], 30)
        self.assertEqual(len(payload["hooks"]["StopFailure"]), 1)

    def test_verify_agent_failure_capture_reports_missing_scripts_and_summarizes_agents(self) -> None:
        summary: list[str] = []
        failures: list[str] = []
        runtime = {
            "agent_failure_capture_script_path": self.workspace / "scripts" / "llm_wiki_agent_failure_capture.py",
            "agent_failure_launcher_paths": {
                "powershell": self.workspace / "scripts" / "run_llm_wiki_agent.ps1",
                "shell": self.workspace / "scripts" / "run_llm_wiki_agent.sh",
                "cmd": self.workspace / "scripts" / "run_llm_wiki_agent.cmd",
            },
            "agent_failure_commands": {
                "claude": "claude",
                "codex": "codex",
            },
        }

        with mock.patch.object(self.module, "command_in_path", side_effect=lambda name: f"C:/tools/{name}.exe" if name == "claude" else None):
            self.module.verify_agent_failure_capture(runtime, summary, failures)

        self.assertTrue(any("Missing agent failure capture script" in failure for failure in failures))
        self.assertTrue(any("Missing agent failure launcher (powershell)" in failure for failure in failures))
        self.assertTrue(any("Agent runtime detected: claude -> C:/tools/claude.exe" in line for line in summary))
        self.assertTrue(any("Agent runtime detected: codex -> missing (codex)" in line for line in summary))

    def test_verify_skill_pipeline_reports_missing_registry_and_dirs(self) -> None:
        failures: list[str] = []
        runtime = {
            "skill_script_path": self.workspace / "scripts" / "llm_wiki_skill_mcp.py",
            "workspace_root": self.workspace,
            "failure_hook_script_path": self.workspace / "scripts" / "llm_wiki_failure_hook.py",
            "skill_registry_path": self.workspace / ".llm-wiki" / "skills-registry.json",
            "skill_pipeline_paths": {
                "brief_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "briefs",
                "delta_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "deltas",
                "validation_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "validations",
                "packet_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "packets",
                "proposal_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "proposals",
                "surrogate_review_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "surrogate-reviews",
                "evolution_run_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "evolution-runs",
                "failure_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "failures",
                "failure_event_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "failures" / "events",
                "failure_cluster_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "failures" / "clusters",
                "failure_benchmark_dir": self.workspace / ".llm-wiki" / "skill-pipeline" / "failures" / "benchmarks",
            },
        }

        self.module.verify_skill_pipeline(runtime, failures)

        self.assertTrue(any("Missing skill MCP script" in failure for failure in failures))
        self.assertTrue(any("Missing skill failure hook script" in failure for failure in failures))
        self.assertTrue(any("Missing skill registry" in failure for failure in failures))
        self.assertTrue(any("Missing skill pipeline brief dir" in failure for failure in failures))

    def test_bootstrap_qmd_defers_embed_failure_without_marking_failure(self) -> None:
        source_path = self.workspace / "memory"
        source_path.mkdir(parents=True, exist_ok=True)
        (self.workspace / "scripts").mkdir(parents=True, exist_ok=True)
        runner = self.workspace / "scripts" / "qmd_embed_runner.mjs"
        runner.write_text("console.log('ok')\n", encoding="utf-8")
        summary: list[str] = []
        failures: list[str] = []
        state: dict[str, object] = {}
        runtime = {
            "qmd_collection": "kade-hq",
            "qmd_source_path": source_path,
            "verify_only": False,
            "qmd_context": "",
            "skip_qmd_embed": False,
            "workspace_root": self.workspace,
        }

        def fake_run(command_name, args, **kwargs):
            if args == ["collection", "list"]:
                return mock.Mock(returncode=0, stdout="kade-hq (qmd://kade-hq/)\n", stderr="")
            if args == ["context", "list"]:
                return mock.Mock(returncode=0, stdout="", stderr="")
            if command_name == "node":
                raise RuntimeError("embed failed")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(self.module, "command_in_path", return_value="node"):
            with mock.patch.object(self.module, "qmd_supports_collections", return_value=True):
                with mock.patch.object(self.module, "run_command", side_effect=fake_run):
                    self.module.bootstrap_qmd(runtime, "pk-qmd", summary, failures, state)

        self.assertTrue(any("qmd embedding deferred" in line for line in summary))
        self.assertFalse(failures)


if __name__ == "__main__":
    unittest.main()
