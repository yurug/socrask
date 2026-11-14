#!/usr/bin/env python3
"""Agents, outcomes, periods, hints and coverage for insights.py."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).with_name("insights.py")


def agent(model, role, requests, tokens, runtime="codex"):
    return {"runtime": runtime, "model": model, "role": role, "requests": requests,
            "input": tokens, "cache_read": 0, "cache_write": 0, "output": 0}


def span(task, day, agents, tier="slice", root="codex:t1", start_h=10):
    total = sum(a["input"] for a in agents)
    return [{"event": "start", "task": task, "at": f"2026-10-{day:02d}T{start_h}:00:00+00:00", "tier": tier,
             "budget": 2 * total or None, "session": None, "cwd": "/r"},
            {"event": "stop", "task": task, "at": f"2026-10-{day:02d}T{start_h}:30:00+00:00",
             "requests": sum(a["requests"] for a in agents), "wall_s": 1800, "active_s": 1200,
             "usage": {a["model"]: {"input": a["input"], "cache_read": 0, "cache_write": 0, "output": 0}
                       for a in agents},
             "agents": agents, "root": root if agents else None, "tools": {}, "checks": {}}]


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        events, feedback = [], []
        for i in range(5):       # the costly model: accepted first 4 times out of 5
            events += span(f"A{i}", 1 + i, [agent("big", "main", 10, 1000), agent("small", "tree_review", 2, 100)],
                           root=f"codex:a{i}")
            feedback.append({"task": f"A{i}", "events": [
                {"at": f"2026-10-{1 + i:02d}T12:00:00Z", "result": "failed" if i == 0 else "accepted"}]})
        for i in range(5):       # the cheap model: accepted first 4 times out of 5
            events += span(f"B{i}", 10 + i, [agent("small", "main", 10, 200)], root=f"codex:b{i}")
            feedback.append({"task": f"B{i}", "events": [
                {"at": f"2026-10-{10 + i:02d}T12:00:00Z", "result": "failed" if i == 4 else "accepted"}]})
        self.events, self.feedback = events, feedback
        self.ledger = {"tasks": [{"id": "A0", "status": "closed", "estimate_hours": 0.5}]
                       + [{"id": f"A{i}", "status": "closed"} for i in range(1, 5)]
                       + [{"id": f"B{i}", "status": "active"} for i in range(5)],
                       "iterations": [{"id": "I1", "start": "2026-10-01", "status": "closed",
                                       "tasks": [f"A{i}" for i in range(5)]},
                                      {"id": "I2", "start": "2026-10-10", "status": "active",
                                       "tasks": [f"B{i}" for i in range(5)]}],
                       "feedback": feedback}

    def run_tool(self, *args, prices=None, code=0):
        (self.root / "meter.jsonl").write_text("".join(json.dumps(e) + "\n" for e in self.events))
        (self.root / "ledger.json").write_text(json.dumps(self.ledger))
        if prices:
            (self.root / "prices.json").write_text(json.dumps(prices))
        result = subprocess.run([sys.executable, str(TOOL), "--meter", "meter.jsonl", "--ledger", "ledger.json",
                                 "--prices", "prices.json", *args], cwd=self.root, capture_output=True,
                                text=True, timeout=20)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_agents_outcomes_and_periods(self):
        out = self.run_tool()
        self.assertIn("10 metered tasks, 0 unmeasured, 0 pairs share a root window.", out)
        self.assertIn("0 metered tasks are absent from the ledger; 10 have a result", out)
        self.assertIn("| codex | big | main | 50 | 5k | 76% | - |", out)
        self.assertIn("| codex:big | slice | 5 | 5 | 80% of 5 | 0 | 1k | - | 20 |", out)
        self.assertIn("| codex:small | slice | 5 | 0 | 80% of 5 | 0 | 200 | - | 20 |", out)
        self.assertIn("| I1 (closed) | 5 | 80% of 5 | 1k |", out)
        self.assertIn("| I2 (active) | 5 | 80% of 5 | 200 |", out)
        self.assertIn("no prices file", out)

    def test_hint_needs_prices_and_enough_tasks(self):
        prices = {"big": {"input": 10}, "small": {"input": 1}}
        out = self.run_tool(prices=prices)
        self.assertIn("- slice: codex:small accepts 80% on the first attempt (5 tasks) at a median $0.00", out)
        self.assertIn("| codex | big | main | 50 | 5k | 76% | $0.05 |", out)
        self.assertIn("No hint", self.run_tool("--min-tasks", "6", prices=prices))

    def test_estimate_ratio_and_weeks_without_iterations(self):
        self.ledger["iterations"] = []
        out = self.run_tool()
        self.assertIn("| 2026-W40 |", out)
        self.assertIn("0.7x", out)       # A0: 20 active minutes against a 0.5 h estimate

    def test_coverage_check(self):
        for i in range(3):
            self.events += span(f"U{i}", 20 + i, [], root=None)
        self.ledger["tasks"] += [{"id": f"U{i}", "status": "active"} for i in range(3)]
        out = self.run_tool("--check", code=1)
        self.assertIn("E-coverage: 3 of the last 13 metered tasks are unmeasured", out)
        self.assertIn("13 metered tasks, 3 unmeasured", out)

    def test_tasks_absent_from_the_ledger_fail_the_check(self):
        self.ledger["tasks"] = self.ledger["tasks"][:5]
        out = self.run_tool("--check", code=1)
        self.assertIn("5 metered tasks are absent from the ledger", out)
        self.assertIn("E-ledger: 5 of the last 10 metered tasks are absent from the ledger", out)

    def test_shared_root_windows_are_counted(self):
        self.events += span("S1", 1, [agent("big", "main", 1, 10)], root="codex:a0")
        self.assertIn("1 pairs share a root window", self.run_tool())


if __name__ == "__main__":
    unittest.main()
