from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_skill_mcp.py"
CLI_ALIAS_PATH = REPO_ROOT / "support" / "scripts" / "llm_wiki_skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_skill_mcp", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SkillPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        temp_root = REPO_ROOT / ".tmp"
        temp_root.mkdir(exist_ok=True)
        self.workspace = temp_root / f"test-skill-mcp-{uuid.uuid4().hex}"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)

    def make_store(self):
        return self.module.SkillStore(self.workspace)

    def base_payload(self) -> dict[str, object]:
        return {
            "title": "Google Flights dropdown requires suggestion click",
            "kind": "ui",
            "applies_to": ["https://www.google.com/travel/flights*"],
            "goal": "Select an airport after typing a city into Google Flights.",
            "trigger": "Apply when Google Flights ignores the typed city until a suggestion row is clicked.",
            "preconditions": "The location field is focused and the suggestion list has had a moment to render.",
            "fast_path": "1. Type the city.\n2. Wait for the suggestion list.\n3. Click the first matching suggestion instead of pressing Enter.\n4. Continue once the chip appears.",
            "failure_modes": "- The suggestion list can render slowly.\n- Pressing Enter before the list appears does nothing.",
            "evidence": "The first run burned several steps by pressing Enter repeatedly. Re-running with a suggestion click removed the exploration cost and completed cleanly.",
            "important_context": "Google Flights looks obvious, but the typed city does not commit on Enter. The agent has to wait for the suggestion list and click a row. This is easy to miss and expensive to rediscover.",
            "observations": [
                "Typing the city and pressing Enter does not select the location.",
                "The suggestion list appears after a short delay.",
                "Clicking the suggestion row creates the location chip immediately.",
            ],
            "risks": ["The dropdown may render slowly on the first load."],
            "next_actions": ["Poll until the suggestion list appears.", "Click the suggestion row instead of submitting early."],
            "files": ["raw/observations/google-flights.md"],
            "references": ["https://www.google.com/travel/flights"],
            "outcome": "The second run skipped the failed Enter attempts and completed in fewer calls.",
        }

    def test_pipeline_run_creates_skill_and_artifacts(self) -> None:
        store = self.make_store()
        result = store.pipeline_run(self.base_payload())

        self.assertEqual(result["status"], "saved")
        skill = result["skill"]
        self.assertEqual(skill["validation_status"], "validated")
        self.assertEqual(skill["memory_scope"], "procedural")
        self.assertEqual(skill["memory_strategy"], "hierarchical")
        self.assertEqual(skill["update_strategy"], "merge_append")
        self.assertTrue(skill["durable_facts"])
        self.assertTrue(skill["retrieval_hints"])
        self.assertTrue(skill["canonical_keys"])
        self.assertTrue(skill["brief_refs"])
        self.assertTrue((self.workspace / result["reflection"]["brief_path"]).exists())
        self.assertTrue((self.workspace / result["packet_path"]).exists())
        self.assertTrue((self.workspace / result["delta_path"]).exists())
        self.assertTrue((self.workspace / result["validation"]["validation_path"]).exists())
        self.assertTrue((self.workspace / "wiki" / "skills" / "active" / f"{skill['id']}.md").exists())
        self.assertEqual(result["packet"]["route_decision"], "complete")
        self.assertIn(skill["id"], result["packet"]["related_skill_ids"])
        self.assertIn(result["delta_path"], result["packet"]["artifact_refs"])
        self.assertIn(result["validation"]["validation_path"], result["packet"]["artifact_refs"])

        log_text = (self.workspace / "wiki" / "log.md").read_text(encoding="utf-8")
        index_text = (self.workspace / "wiki" / "skills" / "index.md").read_text(encoding="utf-8")
        skill_text = (self.workspace / "wiki" / "skills" / "active" / f"{skill['id']}.md").read_text(encoding="utf-8")
        self.assertIn("saved", log_text)
        self.assertIn(skill["id"], index_text)
        self.assertIn("memory_scope:", skill_text)
        self.assertIn("## Durable Facts", skill_text)
        self.assertIn("## Retrieval Hints", skill_text)
        self.assertIn("## Reconciliation Keys", skill_text)
        self.assertIn("packets", store.data)
        self.assertEqual(len(store.data["packets"]), 1)

    def test_lookup_tolerates_legacy_registry_skill_records(self) -> None:
        registry_dir = self.workspace / ".llm-wiki"
        registry_dir.mkdir(parents=True)
        (registry_dir / "skills-registry.json").write_text(
            json.dumps(
                {
                    "skills": {
                        "skill-legacy": {
                            "id": "skill-legacy",
                            "title": "Legacy registry row",
                            "kind": "workflow",
                            "applies_to": ["legacy*"],
                            "created_at": "2026-04-21T00:00:00Z",
                            "updated_at": "2026-04-21T00:00:00Z",
                            "feedback_score": 2,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        store = self.make_store()

        result = store.lookup(goal="legacy registry")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["matches"][0]["id"], "skill-legacy")
        self.assertEqual(result["matches"][0]["status"], "active")

    def test_cli_alias_runs_lookup(self) -> None:
        registry_dir = self.workspace / ".llm-wiki"
        registry_dir.mkdir(parents=True)
        (registry_dir / "skills-registry.json").write_text(
            json.dumps(
                {
                    "skills": {
                        "skill-cli-alias": {
                            "id": "skill-cli-alias",
                            "title": "CLI alias lookup",
                            "kind": "workflow",
                            "trigger": "Use the normal CLI alias for skill lookup.",
                            "applies_to": ["cli*"],
                            "updated_at": "2026-04-21T00:00:00Z",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                sys.executable,
                str(CLI_ALIAS_PATH),
                "--workspace",
                str(self.workspace),
                "lookup",
                "--goal",
                "normal CLI alias lookup",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(proc.stdout)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["matches"][0]["id"], "skill-cli-alias")

    def test_reflect_long_task_writes_packet_and_artifact_refs(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "escalate_to_parent"
        payload["route_reason"] = "Need parent approval before curating a new reusable skill."
        payload["artifact_refs"] = [".llm-wiki/skill-pipeline/validations/example.json"]

        result = store.reflect(payload)

        self.assertEqual(result["status"], "ok")
        self.assertTrue((self.workspace / result["brief_path"]).exists())
        self.assertTrue((self.workspace / result["packet_path"]).exists())
        self.assertEqual(result["packet"]["route_decision"], "escalate_to_parent")
        self.assertIn(result["brief_path"], result["packet"]["artifact_refs"])
        self.assertNotIn("evidence", result["packet"])
        self.assertNotIn("fast_path", result["packet"])
        self.assertNotIn("failure_modes", result["packet"])

    def test_pipeline_auto_merges_duplicates(self) -> None:
        store = self.make_store()
        first = store.pipeline_run(self.base_payload())

        second_payload = self.base_payload()
        second_payload["title"] = "Google Flights airport suggestion click"
        second_payload["observations"] = second_payload["observations"] + [
            "If the list has multiple airports, choose the exact airport name before continuing."
        ]
        second_payload["failure_modes"] = "- Multiple airports can appear for the same city.\n- Pressing Enter too early still fails."
        second_payload["evidence"] = second_payload["evidence"] + "\nA later run also confirmed the multi-airport case."
        second_payload["route_decision"] = "complete"

        second = store.pipeline_run(second_payload)

        self.assertEqual(second["status"], "merged")
        active_files = list((self.workspace / "wiki" / "skills" / "active").glob("*.md"))
        self.assertEqual(len(active_files), 1)
        self.assertGreaterEqual(len(second["skill"]["brief_refs"]), 2)
        self.assertIn("Multiple airports", second["skill"]["failure_modes"])
        self.assertEqual(first["skill"]["id"], second["target_skill_id"])
        self.assertIn(second["target_skill_id"], second["packet"]["related_skill_ids"])
        self.assertEqual(len(store.list_packets(second["target_skill_id"])), 2)

    def test_pipeline_blocks_pii(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["evidence"] = payload["evidence"] + "\nContact user@example.com before retrying."

        result = store.pipeline_run(payload)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("pii_detected", result["reason"])
        self.assertEqual(list((self.workspace / ".llm-wiki" / "skill-pipeline" / "briefs").glob("*.md")), [])
        self.assertEqual(list((self.workspace / ".llm-wiki" / "skill-pipeline" / "packets").glob("*.json")), [])
        self.assertEqual(store.data["skills"], {})

    def test_validate_requires_route_fields_for_non_complete(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "reroute_to_sibling"
        payload["route_reason"] = "Needs a UI-specific agent."

        result = store.validate(payload)

        self.assertEqual(result["status"], "blocked")
        route_checks = {check["name"]: check for check in result["checks"]}
        self.assertEqual(route_checks["route_reroute"]["status"], "fail")
        self.assertIn("assigned_target", route_checks["route_reroute"]["detail"])

    def test_pipeline_run_routes_without_curation_when_non_complete(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "retry_same_worker"
        payload["route_reason"] = "Need one more pass to resolve the flaky dropdown timing."
        payload["unresolved_questions"] = ["What is the minimum wait needed before the suggestion row is clickable?"]

        result = store.pipeline_run(payload)

        self.assertEqual(result["status"], "retry_same_worker")
        self.assertEqual(list((self.workspace / "wiki" / "skills" / "active").glob("*.md")), [])
        self.assertEqual(store.data["skills"], {})
        self.assertEqual(result["packet"]["pipeline_status"], "retry_same_worker")
        self.assertIn(result["delta_path"], result["packet"]["artifact_refs"])

    def test_validate_enforces_hop_and_retry_limits(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["long_task"] = True
        payload["route_decision"] = "escalate_to_parent"
        payload["route_reason"] = "Need a higher-level decision on whether this belongs in the skill library."
        payload["artifact_refs"] = [".llm-wiki/skill-pipeline/briefs/example.md"]
        payload["hop_count"] = 3
        payload["retry_count"] = 2

        result = store.validate(payload)

        self.assertEqual(result["status"], "blocked")
        route_checks = {check["name"]: check for check in result["checks"]}
        self.assertEqual(route_checks["hop_budget"]["status"], "fail")
        self.assertEqual(route_checks["retry_budget"]["status"], "fail")

    def test_evolve_updates_existing_skill_and_frontier(self) -> None:
        store = self.make_store()
        first = store.pipeline_run(self.base_payload())

        evolve_payload = self.base_payload()
        evolve_payload["skill_id"] = first["skill"]["id"]
        evolve_payload["target_skill_id"] = first["skill"]["id"]
        evolve_payload["proposal_action"] = "edit_skill"
        evolve_payload["proposal_reason"] = "Fold the multi-airport fix into the reusable skill."
        evolve_payload["failure_summary"] = "The agent still hesitated when multiple airport suggestions appeared."
        evolve_payload["route_decision"] = "complete"
        evolve_payload["surrogate_verdict"] = "pass"
        evolve_payload["surrogate_findings"] = ["The fix is reusable across Google Flights airport selection flows."]
        evolve_payload["oracle_verdict"] = "pass"
        evolve_payload["benchmark"] = "google-flights-regression"
        evolve_payload["iteration"] = 2
        evolve_payload["program_id"] = "program/iter-2"
        evolve_payload["parent_program_id"] = "program/baseline"
        evolve_payload["observations"] = evolve_payload["observations"] + [
            "When multiple airport rows appear, clicking the exact airport row avoids ambiguous selection."
        ]
        evolve_payload["failure_modes"] = (
            evolve_payload["failure_modes"]
            + "\n- Multiple airport rows can appear for one city and require an exact row click."
        )
        evolve_payload["evidence"] = (
            evolve_payload["evidence"]
            + "\nA later failure showed that selecting the exact airport row fixes the multi-airport variant."
        )

        result = store.evolve(evolve_payload)

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["skill"]["id"], first["skill"]["id"])
        self.assertEqual(result["frontier_entry"]["status"], "accepted")
        self.assertEqual(len(result["frontier"]), 1)
        self.assertTrue((self.workspace / result["proposal_path"]).exists())
        self.assertTrue((self.workspace / result["surrogate_review_path"]).exists())
        self.assertTrue((self.workspace / result["evolution_run_path"]).exists())
        self.assertTrue((self.workspace / ".llm-wiki" / "skill-pipeline" / "frontier.json").exists())

        skill = store.get_skill(first["skill"]["id"])
        assert skill is not None
        self.assertEqual(skill["frontier_status"], "accepted")
        self.assertEqual(skill["evolution_count"], 1)
        self.assertTrue(skill["proposal_refs"])
        self.assertTrue(skill["evolution_run_refs"])
        self.assertTrue(skill["lineage"])

    def test_evolve_discards_when_surrogate_fails(self) -> None:
        store = self.make_store()
        payload = self.base_payload()
        payload["proposal_action"] = "create_skill"
        payload["surrogate_verdict"] = "fail"
        payload["surrogate_summary"] = "The proposed shortcut is too brittle to promote."
        payload["surrogate_findings"] = ["The evidence only covers one narrow timing condition."]

        result = store.evolve(payload)

        self.assertEqual(result["status"], "discarded")
        self.assertIsNone(result["skill"])
        self.assertEqual(store.data["skills"], {})
        self.assertEqual(store.list_frontier(), [])
        self.assertTrue((self.workspace / result["proposal_path"]).exists())
        self.assertTrue((self.workspace / result["surrogate_review_path"]).exists())
        self.assertTrue((self.workspace / result["evolution_run_path"]).exists())
        self.assertEqual(result["frontier_entry"]["status"], "discarded")

    def test_evolve_defaults_iteration_and_baseline_from_existing_skill(self) -> None:
        store = self.make_store()
        first = store.pipeline_run(self.base_payload())
        skill_id = first["skill"]["id"]
        baseline_score = first["skill"]["validation_score"]

        evolve_payload = self.base_payload()
        evolve_payload["skill_id"] = skill_id
        evolve_payload["target_skill_id"] = skill_id
        evolve_payload["proposal_action"] = "edit_skill"
        evolve_payload["proposal_reason"] = "Refine the existing skill without supplying explicit iteration or baseline."
        evolve_payload["route_decision"] = "complete"
        evolve_payload["surrogate_verdict"] = "pass"
        evolve_payload["oracle_verdict"] = "pass"
        evolve_payload["observations"] = evolve_payload["observations"] + [
            "A later run confirmed the same dropdown pattern under a slightly slower render path."
        ]
        evolve_payload["evidence"] = (
            evolve_payload["evidence"]
            + "\nA later run confirmed the same reusable fix under a slower render path."
        )

        result = store.evolve(evolve_payload)

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["proposal"]["iteration"], 1)
        self.assertEqual(result["frontier_entry"]["run_iteration"], 1)
        self.assertEqual(result["evolution_run"]["iteration"], 1)
        self.assertEqual(result["evolution_run"]["baseline_validation_score"], baseline_score)
        self.assertEqual(result["frontier_entry"]["baseline_score"], baseline_score)

    def test_evolve_uses_subjective_pairwise_verifier_for_candidate_win(self) -> None:
        store = self.make_store()
        first = store.pipeline_run(self.base_payload())
        skill_id = first["skill"]["id"]
        title = "Google Flights dropdown ambiguity pairwise"
        benchmark = "google-flights-subjective"
        iteration = 3
        program_id = "program/subjective"
        baseline_first = self.module.deterministic_coin_flip(title, benchmark, iteration, program_id, skill_id, skill_id)
        judge_choice = "B" if baseline_first else "A"

        evolve_payload = self.base_payload()
        evolve_payload["skill_id"] = skill_id
        evolve_payload["target_skill_id"] = skill_id
        evolve_payload["title"] = title
        evolve_payload["proposal_action"] = "edit_skill"
        evolve_payload["proposal_reason"] = "Compare the revised guidance against the baseline on a subjective UX task."
        evolve_payload["benchmark"] = benchmark
        evolve_payload["iteration"] = iteration
        evolve_payload["program_id"] = program_id
        evolve_payload["verification_mode"] = "subjective_pairwise"
        evolve_payload["subjective_task"] = "Choose the better Google Flights guidance for a human operator who needs the clearer workflow."
        evolve_payload["baseline_output"] = "Type the city and press Enter until the airport appears."
        evolve_payload["candidate_output"] = "Type the city, wait for the suggestion list, then click the exact airport row instead of pressing Enter early."
        evolve_payload["judge_choice"] = judge_choice
        evolve_payload["judge_summary"] = "The candidate is more explicit about the ambiguous dropdown and resolves the user intent faster."

        result = store.evolve(evolve_payload)

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["surrogate_review"]["verification_mode"], "subjective_pairwise")
        self.assertEqual(result["surrogate_review"]["verifier_process"], "vmr_pairwise_adapted")
        self.assertEqual(result["surrogate_review"]["winner_source"], "candidate")
        self.assertEqual(result["surrogate_review"]["judge_choice"], judge_choice)
        self.assertIn("return only `A` or `B`", result["surrogate_review"]["judge_prompt"])
        self.assertEqual(len(result["surrogate_review"]["options"]), 2)
        self.assertEqual(result["frontier_entry"]["verification_mode"], "subjective_pairwise")
        self.assertEqual(result["evolution_run"]["verification_mode"], "subjective_pairwise")

    def test_evolve_subjective_pairwise_requires_adjudication_when_no_judge_choice(self) -> None:
        store = self.make_store()
        first = store.pipeline_run(self.base_payload())
        skill_id = first["skill"]["id"]

        evolve_payload = self.base_payload()
        evolve_payload["skill_id"] = skill_id
        evolve_payload["target_skill_id"] = skill_id
        evolve_payload["title"] = "Google Flights dropdown ambiguity pending pairwise"
        evolve_payload["proposal_action"] = "edit_skill"
        evolve_payload["proposal_reason"] = "Stage a subjective verifier packet before accepting the new guidance."
        evolve_payload["verification_mode"] = "subjective_pairwise"
        evolve_payload["subjective_task"] = "Choose the better airport-selection guidance for a human operator."
        evolve_payload["baseline_output"] = "Press Enter after typing the city."
        evolve_payload["candidate_output"] = "Wait for the suggestion list, then click the exact airport row."

        result = store.evolve(evolve_payload)

        self.assertEqual(result["status"], "needs_revision")
        self.assertEqual(result["surrogate_review"]["verification_mode"], "subjective_pairwise")
        self.assertEqual(result["surrogate_review"]["verdict"], "revise")
        self.assertEqual(result["surrogate_review"]["winner_source"], "")
        self.assertIn("pairwise verifier packet", result["surrogate_review"]["summary"].lower())

    def test_mcp_stdio_initialize_and_tools_list(self) -> None:
        proc = subprocess.Popen(
            [sys.executable, str(MODULE_PATH), "--workspace", str(self.workspace), "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )

        def send(message: dict[str, object]) -> None:
            assert proc.stdin is not None
            raw = json.dumps(message).encode("utf-8")
            proc.stdin.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
            proc.stdin.write(raw)
            proc.stdin.flush()

        def receive() -> dict[str, object] | None:
            assert proc.stdout is not None
            headers: dict[str, str] = {}
            while True:
                line = proc.stdout.readline()
                if not line:
                    return None
                if line in (b"\r\n", b"\n"):
                    break
                name, value = line.decode("ascii").split(":", 1)
                headers[name.lower()] = value.strip()
            content_length = int(headers["content-length"])
            body = proc.stdout.read(content_length)
            return json.loads(body.decode("utf-8"))

        try:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest-smoke", "version": "1.0"},
                    },
                }
            )
            initialize = receive()
            self.assertIsNotNone(initialize)
            assert initialize is not None
            self.assertEqual(initialize["result"]["serverInfo"]["name"], "llm-wiki-skills")

            send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            tools = receive()
            self.assertIsNotNone(tools)
            assert tools is not None
            tool_names = [tool["name"] for tool in tools["result"]["tools"]]
            self.assertIn("skill_lookup", tool_names)
            self.assertIn("skill_pipeline_run", tool_names)
        finally:
            if proc.stdin is not None:
                proc.stdin.close()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)

        stderr = proc.stderr.read().decode("utf-8", errors="replace").strip() if proc.stderr is not None else ""
        self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
