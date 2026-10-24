#!/usr/bin/env python3
"""JUnit, TAP and CI-step adapters feed ratchet.py end to end."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
ADAPT, RATCHET = HERE / "ratchet-adapt.py", HERE / "ratchet.py"
JUNIT = """<testsuites><testsuite name="parser">
<testcase classname="parser" name="P3: rejects malformed input"/>
<testcase classname="parser" name="handles unicode"/>
<testcase classname="parser" name="slow path"><skipped/></testcase>
</testsuite></testsuites>"""


class RatchetAdaptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def adapt(self, kind, name, text, code=0):
        src = self.root / name
        src.write_text(text)
        out = subprocess.run([sys.executable, str(ADAPT), kind, str(src)],
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(out.returncode, code, out.stderr)
        return json.loads(out.stdout) if code == 0 else out.stderr

    def ratchet(self, results, code=0):
        path = self.root / "results.json"
        path.write_text(json.dumps(results))
        out = subprocess.run([sys.executable, str(RATCHET), "--from-results", str(path),
                              "--state", str(self.root / ".ratchet.json")],
                             capture_output=True, text=True, timeout=10, cwd=self.root)
        self.assertEqual(out.returncode, code, out.stdout + out.stderr)
        return out.stdout + out.stderr

    def test_junit_maps_property_names_and_suites(self):
        r = self.adapt("junit", "r.xml", JUNIT)
        self.assertTrue(r["complete"])
        self.assertEqual([(t["obligation"], t["status"]) for t in r["tests"]],
                         [("P3", "passed"), ("S-parser", "passed"), ("S-parser", "skipped")])

    def test_junit_failure_and_error_fail(self):
        r = self.adapt("junit", "r.xml", JUNIT.replace('name="handles unicode"/>',
                       'name="handles unicode"><error message="boom"/></testcase>'))
        self.assertIn(("S-parser", "failed"), [(t["obligation"], t["status"]) for t in r["tests"]])

    def test_tap_plan_mismatch_and_bail_out_are_incomplete(self):
        ok = self.adapt("tap", "store.tap", "1..2\nok 1 - T-2 empty input\nok 2 - writes\n")
        self.assertTrue(ok["complete"])
        self.assertEqual(ok["tests"][0]["obligation"], "T-2")
        self.assertEqual(ok["tests"][1]["obligation"], "S-store")
        short = self.adapt("tap", "store.tap", "1..3\nok 1 - a\nok 2 - b\n")
        self.assertFalse(short["complete"])
        bail = self.adapt("tap", "store.tap", "1..1\nBail out! db down\n")
        self.assertFalse(bail["complete"])

    def test_tap_todo_and_skip(self):
        r = self.adapt("tap", "x.tap", "1..2\nnot ok 1 - flaky # TODO later\nok 2 - y # SKIP no db\n")
        self.assertEqual([t["status"] for t in r["tests"]], ["failed", "skipped"])

    def test_steps_receipt_and_running_step(self):
        receipt = {"complete": True, "steps": [{"name": "webapp memory", "status": "passed"},
                                               {"name": "keysvc", "status": "failed"}]}
        r = self.adapt("steps", "results.json", json.dumps(receipt))
        self.assertEqual([t["obligation"] for t in r["tests"]], ["S-webapp-memory", "S-keysvc"])
        receipt["steps"][1]["status"] = "running"
        self.assertFalse(self.adapt("steps", "results.json", json.dumps(receipt))["complete"])

    def test_steps_with_jobs_stay_distinct(self):
        receipt = {"complete": True, "steps": [{"job": "webapp", "name": "unit", "status": "passed"},
                                               {"job": "keysvc", "name": "unit", "status": "timeout"}]}
        r = self.adapt("steps", "r.json", json.dumps(receipt))
        self.assertEqual([(t["obligation"], t["status"]) for t in r["tests"]],
                         [("S-webapp-unit", "passed"), ("S-keysvc-unit", "failed")])

    def test_suite_level_obligations_ratchet_end_to_end(self):
        receipt = {"complete": True, "steps": [{"name": "webapp", "status": "passed"},
                                               {"name": "keysvc", "status": "passed"}]}
        self.ratchet(self.adapt("steps", "r.json", json.dumps(receipt)))
        receipt["steps"].pop()  # a step silently removed from CI
        out = self.ratchet(self.adapt("steps", "r.json", json.dumps(receipt)), code=1)
        self.assertIn("S-keysvc", out)

    def test_duplicate_names_get_stable_distinct_ids(self):
        r = self.adapt("tap", "d.tap", "1..2\nok - same\nok - same\n")
        self.assertEqual(len({t["id"] for t in r["tests"]}), 2)

    def test_unknown_format_is_rejected(self):
        out = subprocess.run([sys.executable, str(ADAPT), "csv", "x"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()
