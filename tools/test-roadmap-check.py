#!/usr/bin/env python3
"""Schedule, risk-ordering and approval checks for roadmap-check.py."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("roadmap-check.py")


def task(tid, deps=(), hours=2, status="planned"):
    return {"id": tid, "plan": "PL-1", "status": status, "depends_on": list(deps),
            "estimate_hours": hours}


BASE = {
    "projects": [{"id": "PR-1", "wip_limit": 2, "roadmap": {
        "milestones": [{"id": "M1", "title": "sync works", "tasks": ["T-spike", "T-sync"],
                        "cases": ["sync-roundtrip"], "retires": ["R1"]}],
        "risks": [{"id": "R1", "statement": "API paginates oddly", "probability": "high",
                   "impact": "high", "retired_by": "T-spike", "blocks": ["T-sync"]}]}}],
    "plans": [{"id": "PL-1", "project": "PR-1"}],
    "tasks": [task("T-spike", hours=3), task("T-ui"), task("T-sync", ["T-spike"], 5),
              task("T-ship", ["T-sync", "T-ui"], 1)],
}


class RoadmapCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger, self.doc = self.root / "ledger.json", self.root / "roadmap.md"
        self.doc.write_text("# Roadmap\n\nWhy this order: the API is the unknown.\n")

    def run_check(self, data, *args, code=0):
        self.ledger.write_text(json.dumps(data))
        result = subprocess.run([sys.executable, str(CHECK), "--ledger", str(self.ledger),
                                 "--doc", str(self.doc), *args],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def approve(self, data):
        digest = self.run_check(data, "--digest", "PR-1").strip()
        data["projects"][0]["roadmap"]["approval"] = {
            "status": "human-complete", "digest": digest,
            "evidence": {"kind": "human-event", "ref": "forebrief:card-7"}}

    def test_schedule_is_generated_and_then_fresh(self):
        data = copy.deepcopy(BASE)
        self.assertIn("E-doc", self.run_check(data, code=1))
        self.run_check(data, "--write")
        text = self.doc.read_text()
        self.assertIn("Why this order", text)
        self.assertIn("| 1 | T-spike, T-ui |", text)
        self.assertIn("Critical path: T-spike -> T-sync -> T-ship (9 h of 11 h total)", text)
        self.assertIn("Widest wave: 2 tasks; WIP limit 2.", text)
        self.run_check(data)
        self.run_check(data, "--write")
        self.assertEqual(text, self.doc.read_text())

    def test_blocked_work_must_follow_the_spike(self):
        data = copy.deepcopy(BASE)
        data["tasks"][2]["depends_on"] = []
        out = self.run_check(data, "--write", code=1)
        self.assertIn("E-risk: PR-1/R1: T-sync does not depend on T-spike", out)

    def test_risk_needs_a_retiring_task(self):
        data = copy.deepcopy(BASE)
        data["projects"][0]["roadmap"]["risks"][0]["retired_by"] = "T-none"
        self.assertIn("E-risk: PR-1/R1 has no known retiring task", self.run_check(data, "--write", code=1))

    def test_late_high_risk_warns(self):
        data = copy.deepcopy(BASE)
        data["tasks"][0]["depends_on"] = ["T-ui"]
        self.assertIn("W-late-risk: PR-1/R1", self.run_check(data, "--write"))

    def test_milestone_needs_cases_and_known_tasks(self):
        data = copy.deepcopy(BASE)
        data["projects"][0]["roadmap"]["milestones"][0].update(cases=[], tasks=["T-ghost"])
        out = self.run_check(data, "--write", code=1)
        self.assertIn("M1 has no acceptance cases", out)
        self.assertIn("M1 names unknown task T-ghost", out)

    def test_cycle_fails(self):
        data = copy.deepcopy(BASE)
        data["tasks"][0]["depends_on"] = ["T-ship"]
        self.assertIn("E-cycle", self.run_check(data, "--write", code=1))

    def test_started_work_needs_current_human_approval(self):
        data = copy.deepcopy(BASE)
        data["tasks"][0]["status"] = "active"
        self.assertIn("E-approval: PR-1 work has started without an approved roadmap",
                      self.run_check(data, "--write", code=1))
        self.approve(data)
        self.run_check(data, "--write")
        data["tasks"][2]["estimate_hours"] = 40
        out = self.run_check(data, "--write", code=1)
        self.assertIn("roadmap changed since approval", out)

    def test_missing_estimates_warn(self):
        data = copy.deepcopy(BASE)
        del data["tasks"][1]["estimate_hours"]
        self.assertIn("W-estimate: PR-1 tasks without estimate_hours: T-ui",
                      self.run_check(data, "--write"))


if __name__ == "__main__":
    unittest.main()
