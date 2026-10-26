#!/usr/bin/env python3
"""Declaration and budget checks for core-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("core-check.py")
HEADER = "# Critical core\n\n| Output | Checker | Budget | Spec |\n|---|---|---|---|\n"
FORMAL = ("# Critical core\n\n| Output | Checker | Budget | Spec | Assurance | Proof | Proved at |\n"
          "|---|---|---|---|---|---|---|\n")


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

    def run_check(self, rows, code=0, header=HEADER, extra=()):
        self.decl.write_text(header + "".join(f"| {' | '.join(r)} |\n" for r in rows))
        result = subprocess.run([sys.executable, str(CHECK), str(self.decl), *extra],
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



class AssuranceTests(CoreCheckTests):
    """A1 and A2 claims hold only while nothing they cover has changed."""

    def setUp(self):
        super().setUp()
        (self.root / "proofs").mkdir()
        (self.root / "proofs" / "Ledger.v").write_text(
            "(* no Admitted here *)\nTheorem sound : True.\nProof. exact I. Qed.\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.commit("proved")
        self.proved = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t",
                               *args], capture_output=True, text=True, check=True).stdout

    def commit(self, message):
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def formal(self, level="A1", proof="`proofs/Ledger.v`", at=None, code=0, extra=()):
        row = ("payouts", "`src/check.ml`", "50", "`kb/models/ledger.md`", level, proof,
               at if at is not None else self.proved)
        return self.run_check([row], code=code, header=FORMAL, extra=extra)

    def test_a1_with_an_unchanged_proof_passes(self):
        self.assertIn("0 errors", self.formal())

    def test_a0_needs_no_proof(self):
        self.assertIn("0 errors", self.formal(level="A0", proof="", at=""))

    def test_unknown_level_fails(self):
        self.assertIn("E-assurance: payouts assurance `A3`", self.formal(level="A3", code=1))

    def test_missing_proof_fails(self):
        self.assertIn("E-proof: payouts proof `proofs/Gone.v`",
                      self.formal(proof="`proofs/Gone.v`", code=1))
        self.assertIn("E-proof: payouts is A2 but names no proof", self.formal("A2", proof="", code=1))

    def test_proved_at_must_be_a_commit(self):
        self.assertIn("E-proved-at: payouts is A1 but `deadbeef`", self.formal(at="deadbeef", code=1))

    def test_a_kernel_change_after_the_proof_is_stale(self):
        (self.root / "src" / "check.ml").write_text("let check _ = false\n")
        out = self.formal("A2", code=1)
        self.assertIn("E-stale: payouts is A2 but changed since", out)
        self.assertIn("src/check.ml", out)

    def test_a_model_change_after_the_proof_is_stale(self):
        (self.root / "kb" / "models" / "ledger.md").write_text("# Ledger model, new invariant\n")
        self.git("commit", "-qam", "change the model")
        self.assertIn("kb/models/ledger.md", self.formal(code=1))

    def test_admitted_goal_fails_but_a_comment_does_not(self):
        (self.root / "proofs" / "Ledger.v").write_text("Theorem sound : False.\nAdmitted.\n")
        self.git("commit", "-qam", "admit")
        at = self.git("rev-parse", "HEAD").strip()
        self.assertIn("E-admit: payouts proof `proofs/Ledger.v` admits", self.formal(at=at, code=1))

    def test_axiom_must_be_trusted_in_the_model(self):
        (self.root / "proofs" / "Ledger.v").write_text("Axiom clock_monotonic : True.\n")
        self.git("commit", "-qam", "axiom")
        at = self.git("rev-parse", "HEAD").strip()
        self.assertIn("E-admit: payouts proof `proofs/Ledger.v` declares axiom `clock_monotonic`",
                      self.formal(at=at, code=1))
        (self.root / "kb" / "models" / "ledger.md").write_text("Trusted: clock_monotonic.\n")
        self.git("commit", "-qam", "trust the clock")
        at = self.git("rev-parse", "HEAD").strip()
        self.assertIn("0 errors", self.formal(at=at))

    def test_lean_sorry_fails(self):
        (self.root / "proofs" / "Ledger.lean").write_text("-- sorry in a comment\ntheorem t : 1 = 1 := sorry\n")
        self.git("add", ".")
        self.commit("lean")
        at = self.git("rev-parse", "HEAD").strip()
        out = self.formal(proof="`proofs/Ledger.lean`", at=at, code=1)
        self.assertIn("E-admit: payouts proof `proofs/Ledger.lean` admits", out)

    def test_report_names_a_stable_a0_kernel_as_a_candidate(self):
        for i in range(3):
            self.commit(f"elsewhere {i}")
        out = self.formal("A0", proof="", at="", extra=("--report", "--window", "3"))
        self.assertIn("report: payouts: A0, 0 of the last 3 commits touch it: candidate", out)
        out = self.formal("A0", proof="", at="", extra=("--report", "--window", "10"))
        self.assertIn("history shorter than the 10-commit window", out)

    def test_report_names_a_recently_changed_kernel_as_moving(self):
        (self.root / "src" / "check.ml").write_text("let check _ = false\n")
        self.git("commit", "-qam", "change the checker")
        out = self.formal("A0", proof="", at="", extra=("--report", "--window", "1"))
        self.assertIn("1 of the last 1 commits touch it: moving", out)


if __name__ == "__main__":
    unittest.main()
