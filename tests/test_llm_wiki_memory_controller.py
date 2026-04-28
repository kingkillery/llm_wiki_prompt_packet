from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_memory_controller.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_memory_controller", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MemoryControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def run_cli(self, workspace: Path, *argv: str) -> dict:
        args = self.module.build_parser().parse_args(["--workspace-root", str(workspace), "--json", *argv])
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(self.module.main_from_args(args), 0)
        return json.loads(stdout.getvalue())

    def test_extract_stages_preference_and_semantic_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            payload = self.run_cli(
                workspace,
                "extract",
                "--text",
                "Remember that I prefer concise final answers. Decision: source evidence remains the source of truth.",
                "--task",
                "memory extraction",
            )

            self.assertEqual(payload["count"], 2)
            kinds = {item["kind"] for item in payload["staged"]}
            self.assertEqual(kinds, {"preference", "semantic"})
            self.assertTrue(all(item["status"] == "pending" for item in payload["staged"]))
            self.assertTrue((workspace / ".llm-wiki" / "memory-ledger" / "events.jsonl").exists())

    def test_extract_honors_min_confidence_and_review_gate_config(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            (workspace / ".llm-wiki").mkdir(parents=True)
            (workspace / ".llm-wiki" / "config.json").write_text(
                json.dumps({"memory_controller": {"review_gate": False, "min_confidence": "high"}}),
                encoding="utf-8",
            )

            filtered = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I prefer short answers.",
                "--task",
                "filtered preference",
            )
            self.assertEqual(filtered["count"], 0)
            self.assertEqual(len(filtered["filtered"]), 1)

            approved = self.run_cli(
                workspace,
                "extract",
                "--text",
                "Remember that I prefer short final answers.",
                "--task",
                "auto approved preference",
            )
            self.assertEqual(approved["count"], 0)
            self.assertEqual(approved["approved"][0]["status"], "approved")

    def test_extract_reads_run_reducer_packet(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            run_dir = workspace / ".llm-wiki" / "skill-pipeline" / "runs" / "run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "reducer_packet.md").write_text(
                "- I prefer CLI approval before durable memory writes.\n",
                encoding="utf-8",
            )

            payload = self.run_cli(workspace, "extract", "--run-id", "run-1", "--task", "run packet")

            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["staged"][0]["source_refs"][0]["run_id"], "run-1")

    def test_approve_apply_projects_semantic_memory(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            extracted = self.run_cli(
                workspace,
                "extract",
                "--text",
                "Decision: approved semantic memories are projected to a generated synthesis page.",
                "--task",
                "projection",
            )
            memory_id = extracted["staged"][0]["id"]

            approved = self.run_cli(workspace, "approve", memory_id, "--apply")

            self.assertEqual(approved["memory"]["status"], "approved")
            projection = workspace / "wiki" / "syntheses" / "memory-ledger-approved.md"
            self.assertTrue(projection.exists())
            self.assertIn(memory_id, projection.read_text(encoding="utf-8"))

    def test_duplicate_reconciliation_merges_into_existing_approved_memory(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            first = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I prefer CLI approval before durable memory writes.",
                "--task",
                "first",
            )
            memory_id = first["staged"][0]["id"]
            self.run_cli(workspace, "approve", memory_id)

            second = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I prefer CLI approval before durable memory writes.",
                "--task",
                "second",
            )

            self.assertEqual(second["count"], 0)
            self.assertEqual(second["merged"][0]["id"], memory_id)

    def test_approving_supersession_expires_old_memory(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            old = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I prefer local memory ranking.",
                "--task",
                "old preference",
            )
            old_id = old["staged"][0]["id"]
            self.run_cli(workspace, "approve", old_id)

            new = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I now prefer local memory ranking instead.",
                "--task",
                "new preference",
            )
            new_memory = new["staged"][0]
            self.assertEqual(new_memory["supersedes"], [old_id])

            approved = self.run_cli(workspace, "approve", new_memory["id"])

            self.assertEqual(approved["expired_superseded"], [old_id])
            old_after = self.run_cli(workspace, "show", old_id)["memory"]
            self.assertEqual(old_after["superseded_by"], new_memory["id"])
            self.assertTrue(old_after["valid_to"])
            ranked = self.run_cli(workspace, "rank", "--query", "local memory ranking")
            self.assertEqual([item["id"] for item in ranked["results"]], [new_memory["id"]])

    def test_approval_blocks_unresolved_contradictions_and_sensitive_memories(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            old = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I prefer local memory ranking.",
                "--task",
                "old preference",
            )
            old_id = old["staged"][0]["id"]
            self.run_cli(workspace, "approve", old_id)
            contradiction = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I never prefer local memory ranking.",
                "--task",
                "contradiction",
            )
            with self.assertRaises(SystemExit):
                self.run_cli(workspace, "approve", contradiction["staged"][0]["id"])
            forced = self.run_cli(workspace, "approve", contradiction["staged"][0]["id"], "--force-contradiction")
            self.assertEqual(forced["memory"]["status"], "approved")

            sensitive = self.run_cli(
                workspace,
                "extract",
                "--text",
                "Remember that I prefer API key token reminders.",
                "--task",
                "sensitive",
            )
            sensitive_id = sensitive["staged"][0]["id"]
            with self.assertRaises(SystemExit):
                self.run_cli(workspace, "approve", sensitive_id)
            approved = self.run_cli(workspace, "approve", sensitive_id, "--force-sensitive")
            self.assertEqual(approved["memory"]["sensitivity"], "credential")

    def test_edit_reject_invalidate_and_rank(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir:
            workspace = Path(workspace_dir)
            extracted = self.run_cli(
                workspace,
                "extract",
                "--text",
                "I prefer memory ranking to emphasize approved high-confidence local preferences.",
                "--task",
                "ranking",
            )
            memory_id = extracted["staged"][0]["id"]
            edited = self.run_cli(
                workspace,
                "edit",
                memory_id,
                "--claim",
                "I prefer approved high-confidence local memory ranking.",
                "--kind",
                "preference",
                "--confidence",
                "high",
            )
            self.assertEqual(edited["memory"]["confidence"], "high")
            self.run_cli(workspace, "approve", memory_id)
            ranked = self.run_cli(workspace, "rank", "--query", "local memory ranking")
            self.assertEqual(ranked["results"][0]["id"], memory_id)
            invalidated = self.run_cli(workspace, "invalidate", memory_id, "--reason", "outdated")
            self.assertEqual(invalidated["memory"]["status"], "invalidated")

            rejected = self.run_cli(
                workspace,
                "extract",
                "--text",
                "Remember that I prefer temporary scratch preferences.",
                "--task",
                "reject",
            )
            rejected_id = rejected["staged"][0]["id"]
            payload = self.run_cli(workspace, "reject", rejected_id)
            self.assertEqual(payload["memory"]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
