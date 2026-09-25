#!/usr/bin/env python3
"""End-to-end input, persistence and concurrent-process regression checks."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

RATCHET = Path(__file__).with_name("ratchet.py")


class RatchetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state.json"

    def command(self, *args):
        return [sys.executable, str(RATCHET), "--state", str(self.state), *args]

    def run_ratchet(self, *args, code=0):
        result = subprocess.run(self.command(*args), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def report(self, entries, **overrides):
        report = {"version": 1, "complete": True, "tests": [
            {"id": str(i), "obligation": c, "status": s} for i, (c, s) in enumerate(entries)]}
        report.update(overrides)
        path = self.root / "results.json"
        path.write_text(json.dumps(report))
        return str(path)

    def test_advance_hold_regress_retire(self):
        self.run_ratchet("--passing", "P1,P2,T3")
        self.assertIn("held at 3", self.run_ratchet("--passing", "P1,P2,T3"))
        self.run_ratchet("--passing", "P1,P2,T3,P4")
        before = self.state.read_bytes()
        self.assertIn("REGRESSED P2", self.run_ratchet("--passing", "P1,T3,P4", code=1))
        self.assertEqual(self.state.read_bytes(), before)
        self.run_ratchet("--retire", "P2", "--reason", "no", code=2)
        self.assertEqual(self.state.read_bytes(), before)
        reason = "P2 merged into P4 by approved design decision"
        self.run_ratchet("--retire", "P2", "--reason", reason)
        self.run_ratchet("--passing", "P1,T3,P4")
        self.assertEqual(json.loads(self.state.read_text())["retired"]["P2"], reason)

    def test_structured_pass_and_mixed_failure(self):
        good = self.report([("P-1", "passed"), ("P1", "passed"), ("NF2", "passed")])
        self.run_ratchet("--from-results", good)
        before = self.state.read_bytes()
        mixed = self.report([("P1", "passed"), ("P1", "failed"), ("NF2", "passed")])
        self.assertIn("FAILED P1", self.run_ratchet("--from-results", mixed, code=1))
        self.assertEqual(self.state.read_bytes(), before)
        self.state.unlink()
        self.run_ratchet("--from-results", mixed, code=1)
        self.assertFalse(self.state.exists())

    def test_skip_is_not_proof(self):
        self.run_ratchet("--passing", "P1")
        before = self.state.read_bytes()
        path = self.report([("P1", "passed"), ("P1", "skipped"), ("P2", "passed")])
        self.assertIn("REGRESSED P1", self.run_ratchet("--from-results", path, code=1))
        self.assertEqual(self.state.read_bytes(), before)
        self.run_ratchet("--from-results", self.report([("P1", "skipped")]), code=1)

    def test_bad_inputs_leave_state_unchanged(self):
        self.run_ratchet("--passing", "P1")
        before = self.state.read_bytes()
        path = self.root / "invalid.json"
        invalid = ["", '{"version":1,', "null", "[]", "{}"]
        for report in [
            {"complete": False}, {"tests": []}, {"version": True},
            {"tests": [{"id": "a", "obligation": "P1", "status": "unknown"}]},
            {"tests": [{"id": "a", "obligation": "P1", "status": "passed"}] * 2},
            {"tests": [{"obligation": "P1", "status": "passed"}]},
        ]:
            invalid.append(Path(self.report([("P1", "passed")], **report)).read_text())
        for content in invalid:
            path.write_text(content)
            self.run_ratchet("--from-results", str(path), code=2)
            self.assertEqual(self.state.read_bytes(), before)
        for args in [("--passing", ""), ("--passing", "not-an-id"), ("--from-log", str(path)), ()]:
            self.run_ratchet(*args, code=2)
            self.assertEqual(self.state.read_bytes(), before)

    def test_dry_run(self):
        self.run_ratchet("--passing", "P1", "--dry-run")
        self.assertFalse(self.state.exists())
        self.run_ratchet("--passing", "P1")
        before = self.state.read_bytes()
        self.run_ratchet("--passing", "P1,P2", "--dry-run")
        self.run_ratchet("--retire", "P1", "--reason", "Retired by the approved decision", "--dry-run")
        self.assertEqual(self.state.read_bytes(), before)

    def test_concurrent_checks_serialize_and_publish_atomically(self):
        # Both candidate snapshots contain the old state but conflict with each
        # other: precisely one may advance; the other must see the new baseline.
        self.run_ratchet("--passing", "P1")
        old_inode = self.state.stat().st_ino
        with open(str(self.state) + ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            processes = [subprocess.Popen(self.command("--passing", ids), stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True) for ids in ["P1,P2", "P1,P3"]]
            try:
                time.sleep(0.2)
                self.assertTrue(all(p.poll() is None for p in processes), "writers must wait on the sidecar lock")
                fcntl.flock(lock, fcntl.LOCK_UN)
                deadline = time.monotonic() + 10
                while any(p.poll() is None for p in processes):
                    self.assertLess(time.monotonic(), deadline, "concurrent writers timed out")
                    self.assertIn(json.loads(self.state.read_text())["passing"], [["P1"], ["P1", "P2"], ["P1", "P3"]])
                    time.sleep(0.001)
                for p in processes:
                    p.communicate(timeout=10)
                self.assertEqual(sorted(p.returncode for p in processes), [0, 1])
                self.assertNotEqual(self.state.stat().st_ino, old_inode)
                self.assertIn(json.loads(self.state.read_text())["passing"], [["P1", "P2"], ["P1", "P3"]])
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.kill()
                    p.communicate()

    def test_concurrent_retirements_preserve_both_reasons(self):
        self.run_ratchet("--passing", "P1,P2,P3")
        processes = [subprocess.Popen(self.command("--retire", c, "--reason", "Retired by approved design decision"),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE) for c in ["P1", "P2"]]
        for p in processes:
            out, err = p.communicate(timeout=10)
            self.assertEqual(p.returncode, 0, (out, err))
        state = json.loads(self.state.read_text())
        self.assertEqual(state["passing"], ["P3"])
        self.assertEqual(set(state["retired"]), {"P1", "P2"})


if __name__ == "__main__":
    unittest.main()
