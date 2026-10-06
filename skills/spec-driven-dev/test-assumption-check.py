#!/usr/bin/env python3
"""Ledger shape and Phase 1 exit-gate checks for assumption-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("assumption-check.py")

HEADER = """---
id: assumptions
type: decision
summary: Choices not yet settled by the KB or a human decision.
domain: process
last-updated: 2026-10-05
---
# Assumption ledger

| ID | Assumption | Status | Basis |
|----|------------|--------|-------|
"""


class AssumptionCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "kb" / "spec").mkdir(parents=True)
        (self.root / "kb" / "spec" / "sync.md").write_text("# Sync\n")
        self.ledger = self.root / "kb" / "assumptions.md"

    def write(self, *rows):
        self.ledger.write_text(HEADER + "".join(f"| {' | '.join(r)} |\n" for r in rows))

    def run_check(self, *args, code=0):
        result = subprocess.run(
            [sys.executable, str(CHECK), str(self.ledger), *args],
            capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_settled_ledger_passes_exit_gate(self):
        self.write(("A1", "Last writer wins", "resolved", "kb/spec/sync.md"),
                   ("A2", "No offline mode in v1", "resolved", "forebrief:q-7"),
                   ("A3", "UTF-8 only", "accepted", "accepted by yann 2026-10-05"))
        self.assertIn("3 assumptions, 0 open", self.run_check("--exit"))

    def test_open_assumption_is_reported_but_allowed_mid_phase(self):
        self.write(("A1", "Retries are idempotent", "open", ""))
        self.assertIn("A1", self.run_check())

    def test_open_assumption_blocks_exit(self):
        self.write(("A1", "Retries are idempotent", "open", ""))
        self.assertIn("E-open: A1", self.run_check("--exit", code=1))

    def test_resolved_needs_existing_kb_path_or_decision(self):
        self.write(("A1", "Last writer wins", "resolved", "kb/spec/missing.md"))
        self.assertIn("E-basis: A1", self.run_check(code=1))
        self.write(("A1", "Last writer wins", "resolved", "I decided"))
        self.assertIn("E-basis: A1", self.run_check(code=1))

    def test_accepted_needs_who_and_when(self):
        self.write(("A1", "UTF-8 only", "accepted", "looks fine"))
        self.assertIn("E-basis: A1", self.run_check(code=1))

    def test_unknown_status_and_duplicate_id_fail(self):
        self.write(("A1", "x", "assumed", ""), ("A1", "y", "open", ""))
        out = self.run_check(code=1)
        self.assertIn("E-status: A1", out)
        self.assertIn("E-dup-id: A1", out)

    def test_missing_ledger_fails(self):
        self.assertIn("E-missing", self.run_check("--exit", code=1))

    def test_ledger_without_table_fails(self):
        self.ledger.write_text(HEADER.split("| ID")[0])
        self.assertIn("E-table", self.run_check(code=1))

    def test_empty_ledger_warns_at_exit(self):
        self.write()
        self.assertIn("W-empty", self.run_check("--exit"))


if __name__ == "__main__":
    unittest.main()
