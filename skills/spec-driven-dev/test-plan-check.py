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
"""

JUDGMENT = """## Step 2: Design retry policy
Tier: judgment
Acceptance:
- `dune test -- -only P9` passes
"""


class PlanCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plan = Path(self.temp.name) / "plan.md"

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

    def test_more_than_four_steps_warns(self):
        steps = "".join(JUDGMENT.replace("Step 2", f"Step {n}") for n in range(1, 6))
        self.assertIn("W-steps: 5 steps", self.run_check(steps))

    def test_other_section_ends_a_step(self):
        out = self.run_check(READY + "\n## Risks\n\nWe might choose wrongly.\n")
        self.assertIn("0 errors", out)


if __name__ == "__main__":
    unittest.main()
