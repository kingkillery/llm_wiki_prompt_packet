"""Regression tests for installers/wire_global_claude.py.

Six permutations cover every mutation path in upsert_section + copy_commands:
  1. Fresh insert into a missing CLAUDE.md (section + backup)
  2. Update existing section WITH end-marker (idempotent replacement)
  3. Update existing section WITHOUT end-marker — heading-fallback preserves
     a subsequent `# Top-Level Heading` (the data-loss regression)
  4. Insert into existing file that has no section yet (append)
  5. copy_commands: fresh copy, identical dest (unchanged), differing dest
     without --force (kept), differing dest with --force (overwritten)
  6. Dry-run produces zero side-effects on disk
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "installers" / "wire_global_claude.py"


def load_module():
    spec = importlib.util.spec_from_file_location("wire_global_claude", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WireGlobalClaudeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.home_dir = tempfile.TemporaryDirectory()
        self.vault_dir = tempfile.TemporaryDirectory()
        self.home = Path(self.home_dir.name)
        self.vault = Path(self.vault_dir.name)
        self.claude_dir = self.home / ".claude"
        self.claude_md = self.claude_dir / "CLAUDE.md"

    def tearDown(self) -> None:
        self.home_dir.cleanup()
        self.vault_dir.cleanup()

    # ------------------------------------------------------------------
    # Permutation 1: fresh insert into a missing CLAUDE.md
    # ------------------------------------------------------------------
    def test_fresh_insert_creates_section_and_backup(self) -> None:
        action, backup_path = self.module.upsert_section(
            self.claude_md,
            self.vault,
            dry_run=False,
            backup=True,
        )

        self.assertEqual(action, "inserted")
        self.assertTrue(self.claude_md.exists())
        text = self.claude_md.read_text(encoding="utf-8")
        self.assertIn("## LLM Wiki", text)
        self.assertIn("<!-- /llm-wiki -->", text)
        self.assertIn(str(self.vault), text)

        # Backup must not be written for a *new* file (nothing to back up).
        self.assertIsNone(backup_path)

    # ------------------------------------------------------------------
    # Permutation 2: update existing section WITH end-marker
    # ------------------------------------------------------------------
    def test_update_section_with_end_marker_is_idempotent(self) -> None:
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        original = (
            "# My Claude\n\n"
            "Some personal notes.\n\n"
            "## LLM Wiki\n\n"
            "Old vault path `/tmp/old-vault`.\n"
            "<!-- /llm-wiki -->\n\n"
            "# Other Section\n\n"
            "More content.\n"
        )
        self.claude_md.write_text(original, encoding="utf-8")

        action, backup_path = self.module.upsert_section(
            self.claude_md,
            self.vault,
            dry_run=False,
            backup=True,
        )

        self.assertEqual(action, "updated")
        self.assertIsNotNone(backup_path)
        self.assertTrue(backup_path.exists())  # type: ignore[unreachable]

        result = self.claude_md.read_text(encoding="utf-8")

        # Vault path was updated.
        self.assertIn(str(self.vault), result)
        self.assertNotIn("/tmp/old-vault", result)

        # The `# Other Section` heading and its content are preserved.
        self.assertIn("# Other Section", result)
        self.assertIn("More content.", result)

        # The top-level heading and early notes are preserved.
        self.assertIn("# My Claude", result)
        self.assertIn("Some personal notes.", result)

        # End-marker is present.
        self.assertIn("<!-- /llm-wiki -->", result)

        # Backup contains the original text.
        backup_text = backup_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
        self.assertIn("/tmp/old-vault", backup_text)

    # ------------------------------------------------------------------
    # Permutation 3: update section WITHOUT end-marker — heading-fallback
    #   must stop at `# ` (not just `## `), preventing data loss of a
    #   subsequent top-level heading.
    # ------------------------------------------------------------------
    def test_heading_fallback_preserves_top_level_heading(self) -> None:
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        original = (
            "# My Claude\n\n"
            "Some personal notes.\n\n"
            "## LLM Wiki\n\n"
            "Old content without end-marker.\n"
            "Still part of old section.\n\n"
            "# Other Section\n\n"
            "This is a top-level heading that must NOT be swallowed.\n"
            "More content under it.\n"
        )
        self.claude_md.write_text(original, encoding="utf-8")

        action, _ = self.module.upsert_section(
            self.claude_md,
            self.vault,
            dry_run=False,
            backup=True,
        )

        self.assertEqual(action, "updated")
        result = self.claude_md.read_text(encoding="utf-8")

        # The top-level heading and its content MUST survive.
        self.assertIn("# Other Section", result)
        self.assertIn("This is a top-level heading that must NOT be swallowed.", result)
        self.assertIn("More content under it.", result)

        # Old content that had no end-marker is replaced.
        self.assertNotIn("Old content without end-marker.", result)
        self.assertNotIn("Still part of old section.", result)

        # New section is present with end-marker.
        self.assertIn(str(self.vault), result)
        self.assertIn("<!-- /llm-wiki -->", result)

    # ------------------------------------------------------------------
    # Permutation 4: insert into existing file that has no section
    # ------------------------------------------------------------------
    def test_insert_appends_section_to_existing_file(self) -> None:
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        original = "# My Claude\n\nJust my personal notes.\n"
        self.claude_md.write_text(original, encoding="utf-8")

        action, _ = self.module.upsert_section(
            self.claude_md,
            self.vault,
            dry_run=False,
            backup=True,
        )

        self.assertEqual(action, "inserted")
        result = self.claude_md.read_text(encoding="utf-8")

        # Original content intact.
        self.assertIn("Just my personal notes.", result)
        # Section appended.
        self.assertIn("## LLM Wiki", result)
        self.assertIn("<!-- /llm-wiki -->", result)

    # ------------------------------------------------------------------
    # Permutation 5: copy_commands — fresh, unchanged, kept, forced
    # ------------------------------------------------------------------
    def test_copy_commands_fresh_unchanged_kept_forced(self) -> None:
        # Set up source: real wiki commands from the repo checkout.
        src_dir = REPO_ROOT / ".claude" / "commands"
        if not src_dir.is_dir():
            self.skipTest("repo .claude/commands/ not found")

        dest_dir = self.claude_dir / "commands"

        # --- Phase A: fresh copy ---
        results = self.module.copy_commands(src_dir, dest_dir, dry_run=False, force=False)
        by_name = {name: status for name, status in results}
        for cmd_name in self.module.WIKI_COMMANDS:
            self.assertEqual(by_name[cmd_name], "copied", f"{cmd_name} should copy fresh")
            self.assertTrue((dest_dir / cmd_name).exists())

        # --- Phase B: identical dest (unchanged) ---
        results2 = self.module.copy_commands(src_dir, dest_dir, dry_run=False, force=False)
        by_name2 = {name: status for name, status in results2}
        for cmd_name in self.module.WIKI_COMMANDS:
            self.assertEqual(by_name2[cmd_name], "unchanged", f"{cmd_name} should be unchanged")

        # --- Phase C: differing dest without --force (kept) ---
        (dest_dir / "wiki-ingest.md").write_text("tampered content\n", encoding="utf-8")
        results3 = self.module.copy_commands(src_dir, dest_dir, dry_run=False, force=False)
        by_name3 = {name: status for name, status in results3}
        self.assertEqual(by_name3["wiki-ingest.md"], "kept (existing differs; pass --force to overwrite)")

        # --- Phase D: differing dest with --force (overwritten) ---
        results4 = self.module.copy_commands(src_dir, dest_dir, dry_run=False, force=True)
        by_name4 = {name: status for name, status in results4}
        self.assertEqual(by_name4["wiki-ingest.md"], "copied")
        restored = (dest_dir / "wiki-ingest.md").read_text(encoding="utf-8")
        self.assertNotIn("tampered", restored)

    # ------------------------------------------------------------------
    # Permutation 6: dry-run produces zero side-effects
    # ------------------------------------------------------------------
    def test_dry_run_writes_nothing(self) -> None:
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        original = "# My Claude\n\nExisting content.\n"
        self.claude_md.write_text(original, encoding="utf-8")

        action, backup_path = self.module.upsert_section(
            self.claude_md,
            self.vault,
            dry_run=True,
            backup=True,
        )

        # The function should report what it *would* do.
        self.assertEqual(action, "inserted")

        # But nothing was actually written.
        self.assertIsNone(backup_path)
        self.assertEqual(
            self.claude_md.read_text(encoding="utf-8"),
            original,
        )

    # ------------------------------------------------------------------
    # Extra: re-running on already-correct file yields "unchanged"
    # ------------------------------------------------------------------
    def test_idempotent_rerun_yields_unchanged(self) -> None:
        action1, _ = self.module.upsert_section(
            self.claude_md,
            self.vault,
            dry_run=False,
            backup=True,
        )
        self.assertEqual(action1, "inserted")

        action2, backup2 = self.module.upsert_section(
            self.claude_md,
            self.vault,
            dry_run=False,
            backup=True,
        )
        self.assertEqual(action2, "unchanged")
        self.assertIsNone(backup2)

    # ------------------------------------------------------------------
    # Extra: missing source dir skips all commands gracefully
    # ------------------------------------------------------------------
    def test_copy_commands_missing_source_dir_skips_all(self) -> None:
        missing = self.home / "nonexistent"
        dest_dir = self.claude_dir / "commands"
        results = self.module.copy_commands(missing, dest_dir, dry_run=False, force=False)
        self.assertEqual(len(results), len(self.module.WIKI_COMMANDS))
        for name, status in results:
            self.assertIn("skipped", status)


if __name__ == "__main__":
    unittest.main()
