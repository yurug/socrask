#!/usr/bin/env python3
"""Component map, drivers, erosion signals and review gate for arch-check.py."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("arch-check.py")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
OVERVIEW = """# Architecture

| Component | Paths | Depends on | Hides | Owns state |
|---|---|---|---|---|
| parser | `src/parser` | - | grammar | - |
| store | `src/store` | - | layout | records |
| api | `src/api` | parser, store | wire format | - |
| ui | `src/ui` | api | widgets | - |
"""
DRIVERS = """# Drivers

| Driver | Source | Served by |
|---|---|---|
| p99 < 50 ms | NF2 | store keeps an in-memory index |
"""


class ArchCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.write("kb/architecture/overview.md", OVERVIEW)
        self.write("kb/architecture/drivers.md", DRIVERS)
        self.commit("kb", ["kb/architecture/overview.md", "kb/architecture/drivers.md"])

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True, env=ENV).stdout.strip()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, msg, files):
        for f in files:
            path = self.root / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(path.read_text() + "x\n" if path.exists() else "x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def run_check(self, *args, code=0):
        result = subprocess.run([sys.executable, str(CHECK), "--root", str(self.root), *args],
                                capture_output=True, text=True, timeout=20, env=ENV)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def review(self, covers, outcome="keep", extra=""):
        self.write("kb/architecture/reviews/2026-10-23-structure.md",
                   f"# Review\n\nCovers: {covers}\nOutcome: {outcome}\n"
                   f"Engineer: forebrief:card-9\n{extra}")

    def test_clean_history_passes(self):
        self.commit("parser", ["src/parser/a.ml"])
        self.commit("api uses parser", ["src/api/a.ml", "src/parser/a.ml"])
        self.assertIn("4 components, 0 errors", self.run_check("--report"))

    def test_hidden_coupling_requires_a_review(self):
        for i in range(5):
            self.commit(f"ui+store {i}", ["src/ui/a.ml", "src/store/a.ml"])
        out = self.run_check(code=1)
        self.assertIn("E-due: store and ui changed together in 5 commits", out)
        self.review(self.git("rev-parse", "HEAD"))
        self.run_check()

    def test_declared_dependency_is_not_hidden_coupling(self):
        for i in range(6):
            self.commit(f"api+store {i}", ["src/api/a.ml", "src/store/a.ml"])
        self.run_check()

    def test_scattered_changes_require_a_review(self):
        for i in range(3):
            self.commit(f"wide {i}", ["src/parser/a.ml", "src/store/a.ml", "src/api/a.ml", "src/ui/a.ml"])
        self.assertIn("3 commits over the whole history each touched 4 or more components",
                      self.run_check(code=1))

    def test_unmapped_files_warn(self):
        self.commit("stray", ["lib/util.ml"])
        self.assertIn("W-unmapped: 1 changed files belong to no component (lib/util.ml)", self.run_check())

    def test_map_and_drivers_are_required(self):
        self.write("kb/architecture/drivers.md", DRIVERS.replace("store keeps an in-memory index", ""))
        self.write("kb/architecture/overview.md", OVERVIEW.replace("parser, store", "parser, cache"))
        out = self.run_check(code=1)
        self.assertIn("E-map: api depends on unknown component cache", out)
        self.assertIn("E-drivers: driver `p99 < 50 ms` says nothing under Served by", out)

    def test_review_record_fields(self):
        self.review("abc", outcome="restructure", extra="ADR: kb/architecture/decisions/ADR-9.md\n")
        self.assertIn("restructures without an existing ADR", self.run_check(code=1))
        self.write("kb/architecture/reviews/2026-10-24-x.md", "# Review\n\nOutcome: maybe\n")
        out = self.run_check(code=1)
        self.assertIn("has no Covers", out)
        self.assertIn("needs Outcome: keep or restructure", out)
        self.assertIn("needs Engineer: forebrief:<card-id>", out)

    def test_completed_milestone_needs_a_review(self):
        ledger = {"projects": [{"id": "PR-1", "roadmap": {"milestones": [
                      {"id": "M1", "tasks": ["T-1"], "cases": ["c"]}]}}],
                  "plans": [], "tasks": [{"id": "T-1", "status": "closed"}]}
        self.write("kb/work/ledger.json", json.dumps(ledger))
        self.assertIn("milestone PR-1/M1 is complete without", self.run_check(code=1))
        self.review(self.git("rev-parse", "HEAD"))
        ledger["projects"][0]["roadmap"]["milestones"][0]["architecture_review"] = \
            "kb/architecture/reviews/2026-10-23-structure.md"
        self.write("kb/work/ledger.json", json.dumps(ledger))
        self.run_check()


if __name__ == "__main__":
    unittest.main()
