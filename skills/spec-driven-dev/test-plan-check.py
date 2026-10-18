#!/usr/bin/env python3
"""Step-shape and execution-readiness checks for plan-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("plan-check.py")

READY = """## Step 1: Sync skeleton through the flaky API
Tier: execution
Obligations: satisfy P3, P7; keep P1
Biggest unknown: whether the API paginates by cursor; stop if it does not.
Files: `src/sync.ml`, `test/test_sync.ml`
Interfaces: `val pull : client -> since:int64 -> item list` in `src/sync.mli`
Acceptance:
- P3: `dune test -- -only P3` passes
- P7: `dune test -- -only P7` passes
Out of scope: retries; we decide them in step 3.
Hand off: if pagination needs a choice the KB does not settle, stop and report.
Proof: preserves `kb/models/sync.md#I2` (the cursor never moves backwards).
  Argument: induction on pulls; each pull sets the cursor to max(old, last item).
  Refinement: `Sync.t.cursor` is the model cursor; `Sync.pull` is `pull`.
"""

JUDGMENT = """## Step 2: Design retry policy
Tier: judgment
Proof: establishes a new invariant I3 on retry counts.
Acceptance:
- `dune test -- -only P9` passes
"""


class PlanCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plan = Path(self.temp.name) / "plan.md"
        models = Path(self.temp.name) / "kb" / "models"
        models.mkdir(parents=True)
        (models / "sync.md").write_text("## Invariants\n- **I2**: the cursor never decreases.\n")

    def run_check(self, text, code=0):
        self.plan.write_text("# Plan\n\n" + text)
        result = subprocess.run([sys.executable, str(CHECK), str(self.plan)],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_ready_plan_passes(self):
        out = self.run_check(READY + "\n" + JUDGMENT)
        self.assertIn("2 steps, 1 execution-tier, 0 errors", out)

    def test_bold_and_bulleted_labels_parse(self):
        text = READY.replace("Tier:", "**Tier:**").replace("Files:", "- **Files**:")
        self.run_check(text)

    def test_missing_file_fails(self):
        result = subprocess.run([sys.executable, str(CHECK), str(self.plan)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E-missing", result.stdout)

    def test_no_steps_fails(self):
        self.assertIn("E-no-steps", self.run_check("Just prose.\n", code=1))

    def test_missing_tier_fails(self):
        out = self.run_check(READY.replace("Tier: execution\n", ""), code=1)
        self.assertIn("E-tier: step 1", out)

    def test_execution_step_needs_every_field(self):
        out = self.run_check(READY.replace("Interfaces:", "Notes:"), code=1)
        self.assertIn("E-field: execution step 1 has no interfaces", out)

    def test_judgment_step_needs_only_tier_and_acceptance(self):
        self.run_check(JUDGMENT)

    def test_acceptance_without_command_fails(self):
        out = self.run_check(READY.replace("- P7: `dune test -- -only P7` passes",
                                           "- P7: sync feels fast"), code=1)
        self.assertIn("E-command: step 1 acceptance `- P7: sync feels fast`", out)

    def test_files_without_paths_fails(self):
        out = self.run_check(READY.replace("`src/sync.ml`, `test/test_sync.ml`",
                                           "the sync module"), code=1)
        self.assertIn("E-files", out)

    def test_open_choice_in_execution_step_fails(self):
        out = self.run_check(READY.replace("in `src/sync.mli`",
                                           "in `src/sync.mli`; choose the error type"), code=1)
        self.assertIn("E-open-choice: execution step 1 (interfaces)", out)

    def test_open_choice_words_inside_code_are_names(self):
        self.run_check(READY.replace("`src/sync.ml`", "`src/choose_peer.ml`, `pick`"))

    def test_open_choice_is_allowed_where_naming_it_is_the_point(self):
        # READY's Out of scope says "decide", Hand off says "choice": both exempt.
        self.run_check(READY)

    def test_open_choice_is_allowed_in_judgment_step(self):
        self.run_check(JUDGMENT.replace("Acceptance:", "Choose a backoff curve.\nAcceptance:"))

    def test_every_step_needs_a_proof(self):
        out = self.run_check(JUDGMENT.replace("Proof: establishes a new invariant I3 on retry counts.\n", ""), code=1)
        self.assertIn("E-field: step 2 has no Proof", out)

    def test_proof_none_needs_a_reason(self):
        text = JUDGMENT.replace("establishes a new invariant I3 on retry counts.", "none")
        self.assertIn("E-proof: step 2 says `Proof: none`", self.run_check(text, code=1))
        self.run_check(text.replace("Proof: none", "Proof: none: documentation only, no behavior"))

    def test_execution_proof_must_cite_an_existing_invariant(self):
        out = self.run_check(READY.replace("sync.md#I2", "sync.md#I9"), code=1)
        self.assertIn("cites I9, which `kb/models/sync.md` does not declare", out)
        out = self.run_check(READY.replace("kb/models/sync.md", "kb/models/gone.md"), code=1)
        self.assertIn("`kb/models/gone.md`, which does not exist", out)
        out = self.run_check(READY.replace("`kb/models/sync.md#I2`", "the cursor invariant"), code=1)
        self.assertIn("cites no `kb/models/<file>.md#I<n>`", out)

    def test_execution_proof_needs_argument_and_refinement(self):
        out = self.run_check(READY.replace("  Argument:", "  Because:"), code=1)
        self.assertIn("has no Argument:", out)
        out = self.run_check(READY.replace("  Refinement:", "  Mapping:"), code=1)
        self.assertIn("has no Refinement:", out)

    def test_budget_is_optional_but_must_be_a_token_count(self):
        self.run_check(READY + "Budget: ~200k tokens\n")
        self.run_check(READY + "Budget: 1.5M\n")
        self.assertIn("E-budget: step 1", self.run_check(READY + "Budget: a lot\n", code=1))

    def test_execution_step_cannot_touch_a_kernel_file(self):
        arch = Path(self.temp.name) / "kb" / "architecture"
        arch.mkdir()
        (arch / "critical-core.md").write_text(
            "| Output | Checker | Budget | Spec |\n|---|---|---|---|\n"
            "| cursor | `src/sync.ml` | 100 | `kb/models/sync.md` |\n")
        out = self.run_check(READY, code=1)
        self.assertIn("E-kernel: execution step 1 touches kernel file `src/sync.ml`", out)
        self.run_check(READY.replace("Tier: execution", "Tier: judgment"))

    def test_more_than_four_steps_warns(self):
        steps = "".join(JUDGMENT.replace("Step 2", f"Step {n}") for n in range(1, 6))
        self.assertIn("W-steps: 5 steps", self.run_check(steps))

    def test_other_section_ends_a_step(self):
        out = self.run_check(READY + "\n## Risks\n\nWe might choose wrongly.\n")
        self.assertIn("0 errors", out)


if __name__ == "__main__":
    unittest.main()
