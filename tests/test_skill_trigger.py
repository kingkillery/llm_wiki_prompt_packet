#!/usr/bin/env python3
"""Tests for skill trigger classifier (M1)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_MODULE_PATH = REPO_ROOT / "support" / "scripts" / "skill_index.py"
TRIGGER_MODULE_PATH = REPO_ROOT / "support" / "scripts" / "skill_trigger.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestSkillIndex(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_index = load_module(INDEX_MODULE_PATH, "skill_index")
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.active_dir = self.workspace / "wiki" / "skills" / "active"
        self.active_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_skill(self, filename: str, content: str) -> None:
        (self.active_dir / filename).write_text(content, encoding="utf-8")

    def test_discover_skills_extracts_frontmatter(self) -> None:
        self._write_skill(
            "git-rebase-workflow.md",
            "---\n"
            "skill_id: skill-git-rebase-workflow\n"
            "title: Git rebase workflow\n"
            "kind: workflow\n"
            "memory_scope: procedural\n"
            "---\n\n"
            "## Trigger\n\n"
            "Use when you need to rebase a feature branch onto main.\n\n"
            "## Fast path\n\n"
            "git rebase main\n",
        )
        skills = self.skill_index.discover_skills(self.active_dir)
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].id, "skill-git-rebase-workflow")
        self.assertEqual(skills[0].title, "Git rebase workflow")
        self.assertEqual(skills[0].trigger, "Use when you need to rebase a feature branch onto main.")
        self.assertEqual(skills[0].fast_path, "git rebase main")

    def test_keyword_score_matches_relevant_task(self) -> None:
        skill = self.skill_index.Skill(
            id="skill-git-rebase",
            title="Git rebase workflow",
            trigger="rebase feature branch onto main",
            fast_path="git rebase main",
        )
        score = self.skill_index._keyword_score("how do I rebase my branch", skill)
        self.assertGreater(score, 0.0)

    def test_keyword_score_zero_for_unrelated_task(self) -> None:
        skill = self.skill_index.Skill(
            id="skill-docker-build",
            title="Docker build workflow",
            trigger="build a docker image from a Dockerfile",
            fast_path="docker build -t myapp .",
        )
        score = self.skill_index._keyword_score("how do I rebase my branch", skill)
        self.assertEqual(score, 0.0)

    def test_build_index_and_load(self) -> None:
        self._write_skill(
            "git-rebase.md",
            "---\nskill_id: skill-git-rebase\ntitle: Git rebase\n---\n\n## Trigger\nrebase branch\n",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        index = self.skill_index.build_index(self.active_dir, output)
        self.assertEqual(len(index.skills), 1)
        self.assertTrue(output.exists())

        loaded = self.skill_index.SkillIndex.load(output)
        self.assertEqual(len(loaded.skills), 1)
        self.assertEqual(loaded.skills[0].id, "skill-git-rebase")

    def test_score_returns_top_n(self) -> None:
        self._write_skill(
            "git-rebase.md",
            "---\nskill_id: skill-git-rebase\ntitle: Git rebase\n---\n\n## Trigger\nrebase branch\n",
        )
        self._write_skill(
            "docker-build.md",
            "---\nskill_id: skill-docker-build\ntitle: Docker build\n---\n\n## Trigger\nbuild docker image\n",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        index = self.skill_index.build_index(self.active_dir, output)
        results = index.score("how do I rebase", top_n=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].id, "skill-git-rebase")
        self.assertGreater(results[0][1], 0.0)

    def test_suggest_skills_filters_by_threshold(self) -> None:
        self._write_skill(
            "git-rebase.md",
            "---\nskill_id: skill-git-rebase\ntitle: Git rebase\n---\n\n## Trigger\nrebase branch\n",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        self.skill_index.build_index(self.active_dir, output)

        # Write a minimal config so suggest_skills can find paths
        config = {"skills": {"active_dir": str(self.active_dir.relative_to(self.workspace))}}
        (self.workspace / ".llm-wiki" / "config.json").write_text(json.dumps(config), encoding="utf-8")

        suggestions = self.skill_index.suggest_skills(self.workspace, "how do I rebase", threshold=0.01)
        self.assertEqual(len(suggestions), 1)

        suggestions = self.skill_index.suggest_skills(self.workspace, "how do I rebase", threshold=0.99)
        self.assertEqual(len(suggestions), 0)

    def test_stub_embedder_is_deterministic(self) -> None:
        embedder = self.skill_index.StubEmbedder(dimensions=8)
        vec1 = embedder.embed("hello")
        vec2 = embedder.embed("hello")
        self.assertEqual(vec1, vec2)
        self.assertAlmostEqual(sum(v * v for v in vec1), 1.0, places=5)


class TestSkillTriggerCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.trigger_module = load_module(TRIGGER_MODULE_PATH, "skill_trigger")
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.active_dir = self.workspace / "wiki" / "skills" / "active"
        self.active_dir.mkdir(parents=True, exist_ok=True)

        # Write a skill
        (self.active_dir / "git-rebase.md").write_text(
            "---\nskill_id: skill-git-rebase\ntitle: Git rebase\n---\n\n## Trigger\nrebase branch\n",
            encoding="utf-8",
        )
        # Build index
        index_module = load_module(INDEX_MODULE_PATH, "skill_index")
        index_module.build_index(self.active_dir, self.workspace / ".llm-wiki" / "skill-index.json")
        config = {"skills": {"active_dir": "wiki/skills/active"}}
        (self.workspace / ".llm-wiki" / "config.json").write_text(json.dumps(config), encoding="utf-8")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_main_finds_skill(self) -> None:
        # Simulate CLI args
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--workspace", default=str(self.workspace))
        parser.add_argument("--task", default="how do I rebase")
        parser.add_argument("--task-file", default="")
        parser.add_argument("--top-n", type=int, default=3)
        parser.add_argument("--threshold", type=float, default=0.01)
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--quiet", action="store_true")
        args = parser.parse_args([])
        args.workspace = str(self.workspace)
        args.task = "how do I rebase"
        args.threshold = 0.01

        # We can't easily call main() because it calls parser.parse_args() internally.
        # Instead test the underlying suggest_skills via skill_index module.
        index_module = load_module(INDEX_MODULE_PATH, "skill_index")
        suggestions = index_module.suggest_skills(self.workspace, "how do I rebase", threshold=0.01)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["id"], "skill-git-rebase")


class TestRecencyDecay(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_index = load_module(INDEX_MODULE_PATH, "skill_index")
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.active_dir = self.workspace / "wiki" / "skills" / "active"
        self.active_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_skill(self, filename: str, content: str) -> None:
        (self.active_dir / filename).write_text(content, encoding="utf-8")

    def test_newer_skill_outranks_stale_skill(self) -> None:
        # Both skills have identical text; only updated_at differs
        self._write_skill(
            "fresh.md",
            "---\n"
            "skill_id: skill-fresh\n"
            "title: Git rebase\n"
            "updated_at: 2026-04-22T10:00:00Z\n"
            "---\n\n## Trigger\nrebase branch\n",
        )
        self._write_skill(
            "stale.md",
            "---\n"
            "skill_id: skill-stale\n"
            "title: Git rebase\n"
            "updated_at: 2026-01-01T10:00:00Z\n"
            "---\n\n## Trigger\nrebase branch\n",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        index = self.skill_index.build_index(self.active_dir, output)
        results = index.score("how do I rebase", halflife_days=30.0)
        self.assertEqual(len(results), 2)
        ids = [r[0].id for r in results]
        self.assertEqual(ids[0], "skill-fresh")
        self.assertEqual(ids[1], "skill-stale")
        # Fresh score should be higher
        self.assertGreater(results[0][1], results[1][1])


class TestGraphTraversal(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_index = load_module(INDEX_MODULE_PATH, "skill_index")
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.active_dir = self.workspace / "wiki" / "skills" / "active"
        self.active_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_skill(self, filename: str, content: str) -> None:
        (self.active_dir / filename).write_text(content, encoding="utf-8")

    def test_neighbors_returned_from_edges(self) -> None:
        self._write_skill(
            "parent.md",
            "---\n"
            "skill_id: skill-parent\n"
            "title: Parent workflow\n"
            "related_skills:\n"
            "  - id: skill-child\n"
            "    relation: prerequisite\n"
            "  - id: skill-conflict\n"
            "    relation: conflict\n"
            "---\n\n## Trigger\nparent task\n",
        )
        self._write_skill(
            "child.md",
            "---\n"
            "skill_id: skill-child\n"
            "title: Child workflow\n"
            "---\n\n## Trigger\nchild task\n",
        )
        self._write_skill(
            "conflict.md",
            "---\n"
            "skill_id: skill-conflict\n"
            "title: Conflict workflow\n"
            "---\n\n## Trigger\nconflict task\n",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        index = self.skill_index.build_index(self.active_dir, output)
        neighbors = index.neighbors("skill-parent", max_per_relation=2)
        self.assertEqual(len(neighbors), 2)
        relations = {n["relation"] for n in neighbors}
        self.assertIn("prerequisite", relations)
        self.assertIn("conflict", relations)

    def test_suggest_skills_includes_neighbors(self) -> None:
        self._write_skill(
            "parent.md",
            "---\n"
            "skill_id: skill-parent\n"
            "title: Parent workflow\n"
            "related_skills:\n"
            "  - id: skill-child\n"
            "    relation: prerequisite\n"
            "---\n\n## Trigger\nrun the parent orchestration\n",
        )
        self._write_skill(
            "child.md",
            "---\n"
            "skill_id: skill-child\n"
            "title: Child workflow\n"
            "---\n\n## Trigger\nrun the child subtask\n",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        self.skill_index.build_index(self.active_dir, output)
        config = {"skills": {"active_dir": str(self.active_dir.relative_to(self.workspace))}}
        (self.workspace / ".llm-wiki" / "config.json").write_text(json.dumps(config), encoding="utf-8")

        suggestions = self.skill_index.suggest_skills(self.workspace, "parent orchestration", threshold=0.01)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["id"], "skill-parent")
        self.assertEqual(len(suggestions[0]["neighbors"]), 1)
        self.assertEqual(suggestions[0]["neighbors"][0]["relation"], "prerequisite")


class TestNegativeExampleFiltering(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_index = load_module(INDEX_MODULE_PATH, "skill_index")
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        self.active_dir = self.workspace / "wiki" / "skills" / "active"
        self.retired_dir = self.workspace / "wiki" / "skills" / "retired"
        self.active_dir.mkdir(parents=True)
        self.retired_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_skill(self, filename: str, content: str, target_dir: Path | None = None) -> None:
        d = target_dir or self.active_dir
        (d / filename).write_text(content, encoding="utf-8")

    def test_retired_skill_gets_penalty(self) -> None:
        self._write_skill("good.md", "---\nskill_id: skill-good\ntitle: Good skill\n---\n\n## Trigger\ngood task\n")
        self._write_skill("bad.md", "---\nskill_id: skill-bad\ntitle: Bad skill\n---\n\n## Trigger\nbad task\n", target_dir=self.retired_dir)
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        index = self.skill_index.build_index(self.active_dir, output)
        self.assertIn("skill-bad", index.penalties)
        self.assertAlmostEqual(index.penalties["skill-bad"], 0.5, places=2)
        self.assertNotIn("skill-good", index.penalties)

    def test_feedback_negative_verdict_penalty(self) -> None:
        self._write_skill("risky.md", "---\nskill_id: skill-risky\ntitle: Risky skill\n---\n\n## Trigger\nrisky task\n")
        pipeline_dir = self.workspace / ".llm-wiki" / "skill-pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "feedback.jsonl").write_text(
            json.dumps({"skill_id": "skill-risky", "verdict": -1, "reason": "failed"}) + "\n",
            encoding="utf-8",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        index = self.skill_index.build_index(self.active_dir, output)
        self.assertIn("skill-risky", index.penalties)
        self.assertAlmostEqual(index.penalties["skill-risky"], 0.25, places=2)

    def test_feedback_penalty_uses_output_workspace_not_active_dir_shape(self) -> None:
        custom_active_dir = self.workspace / "custom" / "skills" / "active"
        custom_retired_dir = self.workspace / "custom" / "skills" / "retired"
        custom_active_dir.mkdir(parents=True, exist_ok=True)
        custom_retired_dir.mkdir(parents=True, exist_ok=True)
        (custom_active_dir / "risky.md").write_text(
            "---\nskill_id: skill-risky\ntitle: Risky skill\n---\n\n## Trigger\nrisky task\n",
            encoding="utf-8",
        )
        pipeline_dir = self.workspace / ".llm-wiki" / "skill-pipeline"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "feedback.jsonl").write_text(
            json.dumps({"skill_id": "skill-risky", "verdict": -1, "reason": "failed"}) + "\n",
            encoding="utf-8",
        )
        output = self.workspace / ".llm-wiki" / "skill-index.json"
        index = self.skill_index.build_index(custom_active_dir, output)
        self.assertEqual(index.penalties.get("skill-risky"), 0.25)

    def test_penalty_reduces_score(self) -> None:
        skill = self.skill_index.Skill(id="skill-bad", title="Bad", trigger="task")
        index = self.skill_index.SkillIndex(skills=[skill], penalties={"skill-bad": 0.5})
        results = index.score("task", top_n=1, halflife_days=30.0)
        self.assertEqual(len(results), 1)
        raw_score = self.skill_index._keyword_score("task", skill)
        expected = raw_score * 0.5
        self.assertAlmostEqual(results[0][1], expected, places=4)

    def test_penalty_capped_at_0_75(self) -> None:
        skill = self.skill_index.Skill(id="skill-awful", title="Awful", trigger="task")
        index = self.skill_index.SkillIndex(skills=[skill], penalties={"skill-awful": 1.0})
        results = index.score("task", top_n=1, halflife_days=30.0)
        self.assertEqual(len(results), 1)
        raw_score = self.skill_index._keyword_score("task", skill)
        expected = raw_score * 0.25
        self.assertAlmostEqual(results[0][1], expected, places=4)


if __name__ == "__main__":
    unittest.main()
