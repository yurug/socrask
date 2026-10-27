#!/usr/bin/env python3
"""Journal, milestone numbers and retrospective gate for retro.py."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RETRO = Path(__file__).with_name("retro.py")


def ledger(closed=True, retrospective=None):
    m2 = {"id": "M2", "tasks": ["T-3", "T-4"]}
    if retrospective:
        m2["retrospective"] = retrospective
    return {"projects": [{"id": "P1", "roadmap": {"milestones": [{"id": "M1", "tasks": ["T-1", "T-2"]}, m2]}}],
            "tasks": [{"id": t, "status": "closed" if closed or t in ("T-1", "T-2") else "active"}
                      for t in ("T-1", "T-2", "T-3", "T-4")],
            "feedback": [{"task": "T-3", "events": [{"at": "2026-10-02T00:00:00Z", "result": "accepted"}]},
                         {"task": "T-4", "events": [{"at": "2026-10-02T00:00:00Z", "result": "failed"},
                                                    {"at": "2026-10-03T00:00:00Z", "result": "failed"},
                                                    {"at": "2026-10-04T00:00:00Z", "result": "accepted"}]}]}


def span(task, day, total, tools=None, checks=None):
    return [{"event": "start", "task": task, "at": f"2026-10-0{day}T10:00:00+00:00", "tier": "slice",
             "budget": None, "session": "s", "cwd": "/r"},
            {"event": "stop", "task": task, "at": f"2026-10-0{day}T11:00:00+00:00", "requests": 3,
             "wall_s": 3600, "active_s": 1200, "usage": {"m": {"input": total, "cache_read": 0,
                                                              "cache_write": 0, "output": 0}},
             "tools": tools or {}, "checks": checks or {}}]


class RetroTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "kb/work").mkdir(parents=True)
        events = (span("T-1", 1, 100) + span("T-2", 1, 300)
                  + span("T-3", 2, 400, {"Bash": [10, 2]}, {"kb-lint.py": [4, 3]})
                  + span("T-4", 3, 600, {"Bash": [5, 0], "Edit": [3, 1]}, {"kb-lint.py": [1, 0]}))
        (self.root / "kb/work/meter.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))

    def write_ledger(self, **kw):
        (self.root / "kb/work/ledger.json").write_text(json.dumps(ledger(**kw)))

    def run_retro(self, *args, code=0):
        result = subprocess.run([sys.executable, str(RETRO), *args, "--root", str(self.root)],
                                capture_output=True, text=True, timeout=20, cwd=self.root,
                                env=dict(os.environ, GIT_DIR=str(self.root / ".git")))
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_record_appends_to_the_git_journal(self):
        self.run_retro("record", "kb-lint", "--exit", "1", "--seconds", "2.5")
        line = json.loads((self.root / ".git/socrask/checks.jsonl").read_text())
        self.assertEqual((line["gate"], line["exit"], line["seconds"]), ("kb-lint", 1, 2.5))

    def test_draft_gives_the_milestone_numbers(self):
        self.write_ledger()
        journal = self.root / ".git/socrask/checks.jsonl"
        journal.parent.mkdir(parents=True)
        journal.write_text("".join(json.dumps(e) + "\n" for e in [
            {"gate": "ratchet", "exit": 1, "seconds": 4, "at": "2026-10-02T10:30:00+00:00"},
            {"gate": "ratchet", "exit": 0, "seconds": 6, "at": "2026-10-03T10:30:00+00:00"},
            {"gate": "ratchet", "exit": 1, "seconds": 9, "at": "2026-10-01T10:30:00+00:00"}]))
        out = self.run_retro("draft", "M2")
        self.assertIn("2 tasks, 2 metered", out)
        self.assertIn("First-attempt acceptance: 1/2 (50%)", out)
        self.assertIn("Repair loops (two or more failed observations): T-4.", out)
        self.assertIn("Median tokens per slice task: 500, previous milestone 200.", out)
        self.assertIn("| Bash | 15 | 2/15 (13%) |", out)
        self.assertIn("| kb-lint.py | 5 | 3/5 (60%) |", out)
        self.assertIn("| ratchet | 2 | 1/2 (50%) | 5 |", out)

    def test_unknown_milestone_is_refused(self):
        self.write_ledger()
        self.assertIn("no single milestone", self.run_retro("draft", "M9", code=1))

    def test_completed_milestone_needs_a_retrospective(self):
        self.write_ledger()
        self.assertIn("E-due: milestone P1/M2", self.run_retro("check", code=1))
        self.write_ledger(closed=False)
        out = self.run_retro("check", code=1)
        self.assertIn("E-due: milestone P1/M1", out)
        self.assertNotIn("P1/M2", out)

    def test_findings_need_a_disposition(self):
        self.write_ledger()
        path = Path(self.run_retro("draft", "P1/M2", "--write").split("wrote ", 1)[1].strip())
        rel = str(path.relative_to(self.root))
        self.write_ledger(retrospective=rel)
        self.assertIn("has no finding", self.run_retro("check", code=1))
        with path.open("a") as f:
            f.write("| F1 | kb-lint.py failed 3/5 | stale index | |\n")
        self.assertIn("finding F1 needs a disposition", self.run_retro("check", code=1))
        path.write_text(path.read_text().replace("stale index | |",
                                                 "stale index | change: kb/INDEX.md regenerated in CI |"))
        out = self.run_retro("check", code=1)
        self.assertIn("E-due: milestone P1/M1", out)
        self.assertNotIn("E-retro", out)

    def test_write_refreshes_only_the_generated_block(self):
        self.write_ledger()
        path = Path(self.run_retro("draft", "M2", "--write").split("wrote ", 1)[1].strip())
        path.write_text(path.read_text().replace("Numbers for", "OLD Numbers for")
                        + "| F1 | x | y | reject: noise |\n")
        self.run_retro("draft", "M2", "--write")
        text = path.read_text()
        self.assertNotIn("OLD", text)
        self.assertIn("| F1 | x | y | reject: noise |", text)


if __name__ == "__main__":
    unittest.main()
