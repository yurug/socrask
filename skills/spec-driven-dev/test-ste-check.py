#!/usr/bin/env python3
"""Writing-standard checks for ste-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("ste-check.py")
GLOSSARY = """# Glossary

- **obligation**: a checkable property ID a step must satisfy. Not: requirement, constraint.
- **step**: one plan entry.
"""
LONG = " ".join(["word"] * 26) + "."


class SteCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "glossary.md").write_text(GLOSSARY)

    def run_check(self, text, code=0):
        doc = self.root / "doc.md"
        doc.write_text(text)
        result = subprocess.run(
            [sys.executable, str(CHECK), str(doc), "--glossary", str(self.root / "glossary.md")],
            capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_short_active_text_is_clean(self):
        out = self.run_check("# Plan\n\nThe worker retries the job. The step must pass.\n")
        self.assertIn("0 errors, 0 warnings", out)

    def test_long_sentence_fails(self):
        self.assertIn("E-long: 26 words (limit 25)", self.run_check(LONG + "\n", code=1))

    def test_sentence_spanning_lines_counts_as_one(self):
        half = " ".join(["word"] * 13)
        self.assertIn("doc.md:1: E-long", self.run_check(f"{half}\n{half}.\n", code=1))

    def test_procedure_step_limit_is_20(self):
        step = "1. " + " ".join(["word"] * 21) + ".\n"
        self.assertIn("(limit 20)", self.run_check(step, code=1))
        self.run_check("- " + " ".join(["word"] * 21) + ".\n")

    def test_code_tables_headings_and_frontmatter_are_skipped(self):
        text = f"---\nsummary: {LONG}\n---\n# {LONG}\n\n```\n{LONG}\n```\n\n| {LONG} |\n"
        self.run_check(text)

    def test_abbreviations_do_not_end_sentences(self):
        self.run_check("Use a tool, e.g. ruff. It runs fast.\n")

    def test_rejected_glossary_word_fails(self):
        self.run_check("Each step lists its requirements.\n", code=1)
        out = self.run_check("Each step lists one requirement.\n", code=1)
        self.assertIn("E-term: `requirement`; the glossary term is `obligation`", out)

    def test_cited_words_are_not_used_words(self):
        self.run_check('Never write "requirement" or *should* here.\n')

    def test_hedge_and_passive_warn_without_failing(self):
        out = self.run_check("The job should be retried by the worker.\n")
        self.assertIn("W-hedge: `should`", out)
        self.assertIn("W-passive: `be retried`", out)

    def test_stdin_input(self):
        result = subprocess.run([sys.executable, str(CHECK), "-", "--glossary",
                                 str(self.root / "glossary.md")],
                                input=LONG, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("-:1: E-long", result.stdout)


if __name__ == "__main__":
    unittest.main()
