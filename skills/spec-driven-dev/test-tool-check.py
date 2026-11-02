#!/usr/bin/env python3
"""Catalog checks for tool-check.py."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("tool-check.py")

HEADER = "# Tools\n\n| Tool | Kind | Does | Test |\n|---|---|---|---|\n"
GEN_ROW = "| `tools/gen-api.py --check` | generate | the client from the schema | `tools/test-gen-api.py` |\n"


class ToolCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("tools/gen-api.py", "print('gen')\n")
        self.write("tools/test-gen-api.py", "pass\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_check(self, catalog=None, *args, code=0):
        if catalog is not None:
            self.write("kb/conventions/tools.md", HEADER + catalog)
        result = subprocess.run([sys.executable, str(CHECK), *args], cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_complete_catalog_passes(self):
        out = self.run_check(GEN_ROW + "| `dune build @fmt` | check | the format | none: the formatter is upstream |\n")
        self.assertIn("2 tools in the catalog, 0 errors", out)

    def test_unlisted_script_fails(self):
        self.write("tools/rename.sh", "sed -i s/a/b/ \"$@\"\n")
        out = self.run_check(GEN_ROW, code=1)
        self.assertIn("E-unlisted: tools/rename.sh is a project script without a row", out)

    def test_tests_fixtures_and_kit_files_need_no_row(self):
        self.write("tools/fixtures/case.py", "pass\n")
        self.write("tools/kb-lint.py", "pass\n")
        self.write("tools/gen_test.py", "pass\n")
        self.write("tools/socrask.json", json.dumps({"files": {"tools/kb-lint.py": {"sha256": "x"}}}))
        self.run_check(GEN_ROW)

    def test_missing_catalog_fails_only_when_scripts_exist(self):
        self.assertIn("E-catalog", self.run_check(code=1))
        (self.root / "tools/gen-api.py").unlink()
        (self.root / "tools/test-gen-api.py").unlink()
        self.run_check()

    def test_row_naming_a_missing_path_fails(self):
        out = self.run_check(GEN_ROW + "| `tools/gone.py` | query | x | none: a short manual query |\n", code=1)
        self.assertIn("E-missing: kb/conventions/tools.md: tool `tools/gone.py` names `tools/gone.py`", out)

    def test_unknown_kind_fails(self):
        out = self.run_check(GEN_ROW.replace("generate", "helper"), code=1)
        self.assertIn("has kind `helper`", out)

    def test_row_needs_an_existing_test_or_a_reason(self):
        out = self.run_check(GEN_ROW.replace("`tools/test-gen-api.py`", ""), code=1)
        self.assertIn("names no test", out)
        out = self.run_check(GEN_ROW.replace("test-gen-api", "test-other"), code=1)
        self.assertIn("names test `tools/test-other.py`, which does not exist", out)
        out = self.run_check(GEN_ROW.replace("`tools/test-gen-api.py`", "none: trivial"), code=1)
        self.assertIn("names no test", out)

    def test_other_directories_are_scanned_on_request(self):
        self.write("scripts/seed.sh", "echo\n")
        self.run_check(GEN_ROW)
        out = self.run_check(GEN_ROW, "--dir", "tools", "--dir", "scripts", code=1)
        self.assertIn("E-unlisted: scripts/seed.sh", out)


if __name__ == "__main__":
    unittest.main()
