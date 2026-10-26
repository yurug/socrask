#!/usr/bin/env python3
"""Marker and config checks for case-leak-check.py."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("case-leak-check.py")


class CaseLeakCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "kb" / "work").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "tests" / "acceptance").mkdir(parents=True)
        (self.root / "tests" / "acceptance" / "refund-overdraft.json").write_text("{}\n")
        (self.root / "src" / "rules.py").write_text("def refund(account):\n    return account.balance\n")
        self.config = self.root / "kb" / "work" / "case-leak.json"

    def run_check(self, config, code=0):
        self.config.write_text(json.dumps(config))
        result = subprocess.run([sys.executable, str(CHECK), str(self.config)],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def config_with(self, **extra):
        return {"version": 1, "sources": ["src/"], "cases": ["tests/acceptance/*.json"], **extra}

    def test_general_code_passes(self):
        self.assertIn("1 files, 1 markers, 0 errors", self.run_check(self.config_with()))

    def test_code_naming_a_case_file_fails(self):
        (self.root / "src" / "rules.py").write_text(
            "def refund(account, case):\n    if case == 'refund-overdraft':\n        return 0\n")
        out = self.run_check(self.config_with(), code=1)
        self.assertIn("src/rules.py:2: E-leak: names acceptance case `refund-overdraft`", out)

    def test_explicit_marker_fails_but_a_longer_word_does_not(self):
        (self.root / "src" / "ids.py").write_text("SPECIAL = 'CASE-42'\nOTHER = 'CASE-421'\n")
        out = self.run_check(self.config_with(markers=["CASE-42"]), code=1)
        self.assertIn("src/ids.py:1: E-leak: names acceptance case `CASE-42`", out)
        self.assertNotIn("ids.py:2", out)

    def test_case_files_inside_sources_are_not_scanned(self):
        out = self.run_check(self.config_with(sources=["src/", "tests/"]))
        self.assertIn("0 errors", out)

    def test_config_needs_sources_and_markers(self):
        self.assertIn("E-config", self.run_check({"version": 1, "sources": ["src/"]}, code=1))
        self.assertIn("E-config", self.run_check({"version": 2}, code=1))
        self.config.unlink()
        result = subprocess.run([sys.executable, str(CHECK), str(self.config)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("E-config", result.stdout)


if __name__ == "__main__":
    unittest.main()
