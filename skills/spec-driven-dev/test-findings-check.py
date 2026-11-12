#!/usr/bin/env python3
"""Convergence cases for findings-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("findings-check.py")
HEAD = "# Findings\n\n| ID | Round | Severity | Finding | Status | Reopened | Evidence |\n|---|---|---|---|---|---|---|\n"


class FindingsCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "findings.md"

    def run_check(self, *rows, extra="", args=(), code=0):
        self.path.write_text(HEAD + "".join(f"| {r} |\n" for r in rows) + extra)
        result = subprocess.run([sys.executable, str(CHECK), str(self.path), *args],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_converging_loop_passes(self):
        out = self.run_check("F1 | 1 | high | a | fixed | | `test_a`",
                             "F2 | 2 | low | b | open | | ",
                             "F3 | 2 | medium | c | rejected | | by design, see ADR-3")
        self.assertIn("3 findings, round 2, 0 errors", out)

    def test_two_striking_rounds_stop_the_loop(self):
        rows = ("F1 | 1 | high | a | fixed | | `test_a`",
                "F2 | 2 | high | b | fixed | | `test_b`",
                "F3 | 3 | high | c | open | | ")
        out = self.run_check(*rows, code=1)
        self.assertIn("E-streak: rounds 2 and 3", out)
        self.run_check(*rows, extra="\nEscalated: round 3, forebrief:C7 (the spec gap goes to Phase 1)\n")

    def test_a_reopened_high_finding_strikes(self):
        out = self.run_check("F1 | 1 | high | a | open | 3 | ",
                             "F2 | 2 | high | b | fixed | | `test_b`", code=1)
        self.assertIn("E-streak: rounds 2 and 3", out)

    def test_round_one_and_low_findings_never_strike(self):
        self.run_check("F1 | 1 | high | a | fixed | | `t`", "F2 | 2 | low | b | open | | ",
                       "F3 | 3 | medium | c | open | | ")

    def test_cap_with_open_high_finding(self):
        rows = ("F1 | 1 | high | a | open | | ", "F2 | 2 | low | b | fixed | | `t`", "F3 | 4 | low | c | open | | ")
        self.assertIn("E-cap: round 4 is past the cap of 3 with high findings open (F1)",
                      self.run_check(*rows, code=1))
        self.run_check(*rows, args=("--max-rounds", "4"))

    def test_evidence_and_shape(self):
        out = self.run_check("F1 | 1 | high | a | fixed | | ", "F2 | 1 | low | b | rejected | | ",
                             "F3 | 1 | severe | c | done | | x", "F4 | two | low | d | open | | ", code=1)
        self.assertIn("E-evidence: F1 is fixed without the test or commit", out)
        self.assertIn("E-evidence: F2 is rejected without the reason", out)
        self.assertIn("E-shape: F3: severity `severe`", out)
        self.assertIn("E-shape: F3: status `done`", out)
        self.assertIn("E-shape: F4: Round and Reopened must be round numbers", out)

    def test_missing_ledger(self):
        result = subprocess.run([sys.executable, str(CHECK), str(self.path) + ".none"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
