#!/usr/bin/env python3
"""Hollow-word and ID-only cases for comment-check.py."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("comment-check.py")


class CommentCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_check(self, files, *args, code=0):
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        result = subprocess.run([sys.executable, str(CHECK), str(self.root), *args],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_hollow_words_warn_across_comment_styles(self):
        out = self.run_check({
            "a.py": "# Handle edge cases robustly.\nx = 1\n",
            "b.ts": "const x = 1; // fail gracefully\n",
            "c.ml": "(* Parse the input properly. *)\nlet x = 1\n",
            "d.c": "/* Multi-line block\n * kept for safety\n */\nint x;\n",
        }, "--all")
        self.assertEqual(out.count("W-hollow"), 4, out)
        self.assertIn("a.py:1: W-hollow: `edge cases`", out)
        self.assertIn("d.c:2: W-hollow: `for safety`", out)

    def test_id_only_comments_warn_and_claims_with_ids_pass(self):
        out = self.run_check({
            "a.ts": "// enforces P4\n// per ADR-007\nconst y = 2;\n// see kb/models/sync.md#I2\n",
            "b.ts": "// The cursor never decreases, so a retry never emits twice (P4).\nconst z = 3;\n",
        })
        self.assertEqual(out.count("W-id-only"), 2, out)
        self.assertIn("a.ts:1: W-id-only", out)
        self.assertIn("a.ts:4: W-id-only", out)
        self.assertNotIn("b.ts", out)

    def test_a_run_of_line_comments_is_one_comment(self):
        out = self.run_check({"a.py": "# P4\n# The cursor never decreases, so a retry\n# never emits twice.\n"})
        self.assertNotIn("W-id-only", out)

    def test_paths_and_plain_words_are_not_hollow(self):
        out = self.run_check({"a.ts": "// kb/properties/edge-cases.md lists the empty input.\n"
                                      "// Each exercise stays open until it is answered correctly.\n"})
        self.assertIn("0 warnings", out)

    def test_code_and_strings_outside_comments_are_ignored(self):
        self.run_check({"a.py": "robust = 'properly'\nurl = 'http://x/y'\n"})
        out = self.run_check({"b.ts": "const u = 'http://example.org';\n"})
        self.assertIn("0 warnings", out)

    def test_suppression_needs_a_reason(self):
        out = self.run_check({"a.py": "# comment-check: ok the RFC term is robust\n# robust\n",
                              "b.py": "# robust comment-check: ok\n"})
        self.assertNotIn("a.py", out)
        self.assertIn("b.py:1: W-hollow", out)

    def test_strict_fails_and_many_warnings_group(self):
        files = {f"f{i}.py": "# done properly\n" for i in range(5)}
        out = self.run_check(files, "--strict", code=1)
        self.assertIn("W-hollow: 5 warnings, first at", out)
        self.assertEqual(self.run_check(files, "--all").count("W-hollow"), 5)


if __name__ == "__main__":
    unittest.main()
