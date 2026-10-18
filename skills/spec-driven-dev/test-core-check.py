#!/usr/bin/env python3
"""Declaration and budget checks for core-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("core-check.py")
HEADER = "# Critical core\n\n| Output | Checker | Budget | Spec |\n|---|---|---|---|\n"


class CoreCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "kb" / "architecture").mkdir(parents=True)
        (self.root / "kb" / "models").mkdir()
        (self.root / "kb" / "models" / "ledger.md").write_text("# Ledger model\n")
        (self.root / "src").mkdir()
        (self.root / "src" / "check.ml").write_text("let check _ = true\n" * 40)
        self.decl = self.root / "kb" / "architecture" / "critical-core.md"

    def run_check(self, rows, code=0):
        self.decl.write_text(HEADER + "".join(f"| {' | '.join(r)} |\n" for r in rows))
        result = subprocess.run([sys.executable, str(CHECK), str(self.decl)],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_kernel_within_budget_passes(self):
        out = self.run_check([("payouts", "`src/check.ml`", "50", "`kb/models/ledger.md#I1`")])
        self.assertIn("payouts: 40/50 lines", out)

    def test_kernel_over_budget_fails(self):
        out = self.run_check([("payouts", "`src/check.ml`", "30", "`kb/models/ledger.md`")], code=1)
        self.assertIn("E-budget: payouts checker is 40 lines, over its budget of 30", out)

    def test_missing_checker_file_fails(self):
        out = self.run_check([("payouts", "`src/gone.ml`", "30", "`kb/models/ledger.md`")], code=1)
        self.assertIn("E-file: payouts checker `src/gone.ml` does not exist", out)

    def test_spec_must_be_an_existing_model(self):
        out = self.run_check([("payouts", "`src/check.ml`", "50", "`kb/spec/ledger.md`")], code=1)
        self.assertIn("E-spec", out)

    def test_budget_must_be_a_number(self):
        out = self.run_check([("payouts", "`src/check.ml`", "small", "`kb/models/ledger.md`")], code=1)
        self.assertIn("E-budget: payouts budget `small`", out)

    def test_empty_table_and_missing_file_fail(self):
        self.assertIn("E-table", self.run_check([], code=1))
        self.decl.unlink()
        result = subprocess.run([sys.executable, str(CHECK), str(self.decl)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E-missing", result.stdout)


if __name__ == "__main__":
    unittest.main()
