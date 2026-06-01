from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "support" / "scripts" / "llm_wiki_agent_updater_hook.py"


class AgentUpdaterHookTests(unittest.TestCase):
    def test_disabled_hook_records_event_without_launching_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            env = dict(os.environ)
            env["LLM_WIKI_UPDATER_ENABLED"] = "0"
            payload = {"hook_event_name": "SessionStart", "source": "startup"}

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "codex",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            response = json.loads(completed.stdout)
            self.assertTrue(response["continue"])
            state = workspace / ".llm-wiki" / "state" / "agent-updater"
            self.assertTrue((state / "hook-events.jsonl").exists())
            audit = json.loads((state / "hook-events.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(audit["agent"], "codex")
            self.assertEqual(audit["event"], "SessionStart")
            self.assertEqual(audit["reason"], "disabled")
            self.assertTrue(list((state / "events").glob("*.json")))
            context_state = workspace / ".llm-wiki" / "state" / "context-layer"
            manifest = json.loads((context_state / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["counters"]["events_recorded"], 1)
            self.assertEqual(manifest["counters"]["jobs_enqueued"], 0)
            self.assertEqual(manifest["last_event"]["event"], "SessionStart")
            self.assertTrue((context_state / "events.jsonl").exists())

    def test_inline_hook_runs_local_memory_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Remember that this repo should keep updater hooks enabled for Claude and Codex.",
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "claude",
                    "--inline",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            runs_path = workspace / ".llm-wiki" / "state" / "agent-updater" / "runs.jsonl"
            self.assertTrue(runs_path.exists())
            run = json.loads(runs_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(run["agent"], "claude")
            self.assertEqual(run["event"], "UserPromptSubmit")
            self.assertIn(run["memory_extract"]["status"], {"ok", "failed"})

    def test_codex_event_name_and_input_payload_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = {
                "event_name": "UserPromptSubmit",
                "input": "Remember that Codex hook payloads may use input instead of prompt.",
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "codex",
                    "--inline",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            event_files = list((workspace / ".llm-wiki" / "state" / "agent-updater" / "events").glob("*.json"))
            self.assertEqual(len(event_files), 1)
            event = json.loads(event_files[0].read_text(encoding="utf-8"))
            self.assertEqual(event["hook_event_name"], "UserPromptSubmit")

    def test_user_prompt_submit_path_and_url_enqueue_context_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            env = dict(os.environ)
            env["LLM_WIKI_UPDATER_ENABLED"] = "0"
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Summarize ./README.md and https://example.com/diagram.png before answering.",
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "codex",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            context_state = workspace / ".llm-wiki" / "state" / "context-layer"
            jobs = list((context_state / "queue").glob("*.json"))
            self.assertEqual(len(jobs), 1)
            job = json.loads(jobs[0].read_text(encoding="utf-8"))
            self.assertEqual(job["agent"], "codex")
            self.assertEqual(job["event"], "UserPromptSubmit")
            self.assertIn("path-reference", job["triggers"])
            self.assertIn("url-reference", job["triggers"])
            self.assertIn("media-reference", job["triggers"])
            self.assertIn("./README.md", job["references"]["paths"])
            self.assertNotIn("//example.com/diagram.png", job["references"]["paths"])
            self.assertIn("https://example.com/diagram.png", job["references"]["urls"])
            manifest = json.loads((context_state / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["counters"]["jobs_enqueued"], 1)
            self.assertEqual(manifest["counters"]["queue_depth"], 1)

    def test_user_prompt_submit_url_only_does_not_enqueue_path_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            env = dict(os.environ)
            env["LLM_WIKI_UPDATER_ENABLED"] = "0"
            payload = {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Inspect https://example.com/diagram.png before answering.",
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "codex",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            context_state = workspace / ".llm-wiki" / "state" / "context-layer"
            jobs = list((context_state / "queue").glob("*.json"))
            self.assertEqual(len(jobs), 1)
            job = json.loads(jobs[0].read_text(encoding="utf-8"))
            self.assertIn("url-reference", job["triggers"])
            self.assertIn("media-reference", job["triggers"])
            self.assertNotIn("path-reference", job["triggers"])
            self.assertEqual(job["references"]["paths"], [])
            self.assertEqual(job["references"]["urls"], ["https://example.com/diagram.png"])

    def test_post_tool_use_event_can_inject_context_and_run_inline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "README.md"},
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "claude",
                    "--inline",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            response = json.loads(completed.stdout)
            self.assertTrue(response["continue"])
            self.assertEqual(response["hookSpecificOutput"]["hookEventName"], "PostToolUse")
            self.assertIn("additionalContext", response["hookSpecificOutput"])
            state = workspace / ".llm-wiki" / "state" / "agent-updater"
            audit = json.loads((state / "hook-events.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertFalse(audit["launched"])
            self.assertEqual(audit["reason"], "context-layer-only-event")
            context_state = workspace / ".llm-wiki" / "state" / "context-layer"
            jobs = list((context_state / "queue").glob("*.json"))
            self.assertEqual(len(jobs), 1)
            job = json.loads(jobs[0].read_text(encoding="utf-8"))
            self.assertEqual(job["event"], "PostToolUse")
            self.assertEqual(job["tool_name"], "Read")
            self.assertIn("tool-observation:Read", job["triggers"])
            self.assertIn("README.md", job["references"]["paths"])

    def test_post_tool_use_non_inline_records_context_without_launching_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            large_response = "observed output " + ("x" * 6000)
            payload = {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "README.md", "api_token": "secret-token-value"},
                "tool_response": large_response,
            }

            completed = subprocess.run(
                [
                    sys.executable,
                    str(HOOK),
                    "--workspace",
                    str(workspace),
                    "--agent",
                    "claude",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            state = workspace / ".llm-wiki" / "state" / "agent-updater"
            audit = json.loads((state / "hook-events.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertFalse(audit["launched"])
            self.assertEqual(audit["reason"], "context-layer-only-event")
            self.assertFalse((state / "worker.out.log").exists())
            event_files = list((state / "events").glob("*.json"))
            self.assertEqual(len(event_files), 1)
            persisted_event = json.loads(event_files[0].read_text(encoding="utf-8"))
            self.assertTrue(persisted_event["llm_wiki_payload_sanitized"])
            self.assertEqual(persisted_event["tool_input"]["api_token"], "[redacted]")
            self.assertIn("...[truncated]", persisted_event["tool_response"])
            self.assertNotIn("x" * 5000, event_files[0].read_text(encoding="utf-8"))
            self.assertNotIn("secret-token-value", event_files[0].read_text(encoding="utf-8"))
            context_state = workspace / ".llm-wiki" / "state" / "context-layer"
            jobs = list((context_state / "queue").glob("*.json"))
            self.assertEqual(len(jobs), 1)
            job = json.loads(jobs[0].read_text(encoding="utf-8"))
            self.assertEqual(job["event"], "PostToolUse")
            self.assertIn("tool-observation:Read", job["triggers"])
            self.assertIn("...[truncated]", job["content_preview"])
            self.assertNotIn("secret-token-value", json.dumps(job))


if __name__ == "__main__":
    unittest.main()
