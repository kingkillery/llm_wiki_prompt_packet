from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "installers" / "wire_repo_agent_hooks.py"


def load_module():
    spec = importlib.util.spec_from_file_location("wire_repo_agent_hooks", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WireRepoAgentHooksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_codex_config_merges_existing_features_table(self) -> None:
        config_path = self.workspace / ".codex" / "config.toml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("[features]\nplugins = true\n\n[tools]\nweb_search = true\n", encoding="utf-8")

        actions = self.module.merge_codex_config(self.workspace, dry_run=False)

        self.assertIn("write", actions[0])
        parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertTrue(parsed["features"]["plugins"])
        self.assertTrue(parsed["features"]["hooks"])
        self.assertTrue(parsed["tools"]["web_search"])
        self.assertIn("UserPromptSubmit", parsed["hooks"])
        self.assertEqual(config_path.read_text(encoding="utf-8").count("[features]"), 1)

    def test_claude_settings_merge_preserves_existing_keys(self) -> None:
        settings_path = self.workspace / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(json.dumps({"permissions": {"allow": ["Read"]}}), encoding="utf-8")

        actions = self.module.merge_claude_settings(self.workspace, force=False, dry_run=False)

        self.assertIn("write", actions[0])
        parsed = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(parsed["permissions"], {"allow": ["Read"]})
        self.assertIn("UserPromptSubmit", parsed["hooks"])
        self.assertIn("llm_wiki_agent_updater_hook.py", parsed["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"])
        self.assertIn("PostToolUse", parsed["hooks"])
        self.assertEqual(parsed["hooks"]["PostToolUse"][0]["matcher"], "*")
        self.assertIn("llm_wiki_agent_updater_hook.py", parsed["hooks"]["PostToolUse"][0]["hooks"][0]["command"])

    def test_claude_settings_merge_preserves_existing_post_tool_use_hooks(self) -> None:
        settings_path = self.workspace / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PostToolUse": [
                            {
                                "matcher": "Read",
                                "hooks": [
                                    {"type": "command", "command": "echo custom"}
                                ],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        self.module.merge_claude_settings(self.workspace, force=False, dry_run=False)
        self.module.merge_claude_settings(self.workspace, force=False, dry_run=False)

        parsed = json.loads(settings_path.read_text(encoding="utf-8"))
        post_groups = parsed["hooks"]["PostToolUse"]
        self.assertEqual(len(post_groups), 2)
        self.assertEqual(post_groups[0]["matcher"], "Read")
        self.assertEqual(post_groups[0]["hooks"][0]["command"], "echo custom")
        self.assertEqual(post_groups[1]["matcher"], "*")
        self.assertIn("llm_wiki_agent_updater_hook.py", post_groups[1]["hooks"][0]["command"])

    def test_copy_hook_scripts_installs_worker_and_hook(self) -> None:
        actions = self.module.copy_hook_scripts(self.workspace, force=False, dry_run=False)

        self.assertEqual(len(actions), 2)
        self.assertTrue((self.workspace / "scripts" / "llm_wiki_agent_updater.py").exists())
        self.assertTrue((self.workspace / "scripts" / "llm_wiki_agent_updater_hook.py").exists())

    def test_self_test_exercises_installed_codex_hook(self) -> None:
        self.module.copy_hook_scripts(self.workspace, force=False, dry_run=False)

        ok, message = self.module.run_self_test(self.workspace, "codex")

        self.assertTrue(ok, message)
        state = self.workspace / ".llm-wiki" / "state" / "agent-updater"
        self.assertTrue((state / "hook-events.jsonl").exists())
        event = json.loads((state / "hook-events.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(event["agent"], "codex")
        self.assertEqual(event["event"], "UserPromptSubmit")


if __name__ == "__main__":
    unittest.main()
