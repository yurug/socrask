#!/usr/bin/env python3
"""Scope cases for scope-check.py, on a scratch git repository."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("scope-check.py")

PLAN = """# Plan

## Step 1: Sync skeleton
Tier: execution
Files: `src/sync.ml`, `test/` (new tests), `gen/*.json`
Acceptance:
- `dune test` passes

## Step 2: Docs
Tier: judgment
Acceptance:
- `make docs` passes
"""


class ScopeCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.write("kb/plan.md", PLAN)
        self.write("src/sync.ml", "let x = 1\n")
        self.write("src/other.ml", "let y = 2\n")
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True).stdout

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_check(self, *args, step="1", code=0):
        result = subprocess.run([sys.executable, str(CHECK), "kb/plan.md", "--step", step,
                                 "--base", self.base, *args],
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_declared_files_dirs_globs_and_kb_pass(self):
        self.write("src/sync.ml", "let x = 2\n")
        self.write("test/test_sync.ml", "let () = ()\n")
        self.write("gen/api.json", "{}\n")
        self.write("kb/models/sync.md", "# Sync\n")
        self.assertIn("4 changed files, 0 outside", self.run_check())

    def test_undeclared_change_fails_committed_or_not(self):
        self.write("src/other.ml", "let y = 3\n")
        self.write("src/new_helper.ml", "let z = 0\n")
        out = self.run_check(code=1)
        self.assertIn("E-scope: src/other.ml changed, but step 1 does not declare it", out)
        self.assertIn("E-scope: src/new_helper.ml", out)
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "work")
        self.assertIn("2 outside", self.run_check(code=1))

    def test_rename_counts_both_sides(self):
        self.git("mv", "src/sync.ml", "src/moved.ml")
        out = self.run_check(code=1)
        self.assertIn("E-scope: src/moved.ml", out)
        self.assertNotIn("E-scope: src/sync.ml", out)

    def test_allow_adds_a_glob(self):
        self.write("CHANGELOG.md", "x\n")
        self.run_check(code=1)
        self.run_check("--allow", "CHANGELOG.md")

    def test_unusable_input(self):
        self.assertIn("no step 9", self.run_check(step="9", code=2))
        self.assertIn("declares no Files", self.run_check(step="2", code=2))
        result = subprocess.run([sys.executable, str(CHECK), "kb/plan.md", "--step", "1", "--base", "nope"],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout)


if __name__ == "__main__":
    unittest.main()
