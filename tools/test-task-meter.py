#!/usr/bin/env python3
"""Attribution, report and retrospective checks for task-meter.py."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

METER = Path(__file__).with_name("task-meter.py")
NOW = datetime.now(timezone.utc)


def ts(minutes_ago):
    return (NOW - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")


def claude_line(minutes_ago, session, request, inp=10, read=1000, write=100, out=50,
                cwd="/repo", model="claude-x"):
    return json.dumps({"type": "assistant", "timestamp": ts(minutes_ago), "sessionId": session,
                       "requestId": request, "cwd": cwd, "message": {"model": model, "usage": {
                           "input_tokens": inp, "cache_read_input_tokens": read,
                           "cache_creation_input_tokens": write, "output_tokens": out}}})


class TaskMeterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.claude = self.root / "claude"
        self.codex = self.root / "codex"
        (self.claude / "proj" / "s1" / "subagents").mkdir(parents=True)
        self.codex.mkdir()
        self.meter = self.root / "kb" / "work" / "meter.jsonl"
        self.meter.parent.mkdir(parents=True)

    def run_meter(self, *args, code=0, cwd=None):
        result = subprocess.run(
            [sys.executable, str(METER), *args, "--meter", str(self.meter),
             "--claude-dir", str(self.claude), "--codex-dir", str(self.codex)],
            capture_output=True, text=True, timeout=20, cwd=cwd or self.root)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def start_at(self, task, minutes_ago, session: "str | None" = "s1", cwd="/repo", tier="slice", budget=None):
        with self.meter.open("a") as f:
            f.write(json.dumps({"event": "start", "task": task, "at": ts(minutes_ago), "tier": tier,
                                "budget": budget, "session": session, "cwd": cwd}) + "\n")

    def stop_event(self, task, total, tier="slice"):
        with self.meter.open("a") as f:
            f.write(json.dumps({"event": "start", "task": task, "at": ts(9), "tier": tier,
                                "budget": None, "session": None, "cwd": "/x"}) + "\n")
            f.write(json.dumps({"event": "stop", "task": task, "at": ts(8), "requests": 1,
                                "wall_s": 60, "active_s": 60, "usage": {"m": {
                                    "input": total, "cache_read": 0, "cache_write": 0,
                                    "output": 0}}}) + "\n")

    def test_session_window_and_dedup(self):
        lines = [claude_line(30, "s1", "r0"),                 # before start
                 claude_line(5, "s1", "r1"),
                 claude_line(4, "s1", "r2"), claude_line(4, "s1", "r2"),  # same request twice
                 claude_line(3, "s2", "r3")]                  # other session
        (self.claude / "proj" / "s1.jsonl").write_text("\n".join(lines) + "\n")
        (self.claude / "proj" / "s1" / "subagents" / "agent-a.jsonl").write_text(
            claude_line(3, "s1", "r4", model="claude-small") + "\n")
        self.start_at("T-1", 10)
        out = self.run_meter("stop", "T-1")
        self.assertIn("over 3 requests", out)
        stop = json.loads(self.meter.read_text().splitlines()[-1])
        self.assertEqual(stop["usage"]["claude-x"]["cache_read"], 2000)
        self.assertEqual(stop["usage"]["claude-small"]["output"], 50)

    def test_without_session_attribution_uses_cwd_and_codex(self):
        (self.claude / "proj" / "s9.jsonl").write_text(
            claude_line(5, "s9", "r1", cwd="/repo/sub") + "\n" +
            claude_line(5, "s9", "r2", cwd="/elsewhere") + "\n")
        (self.codex / "rollout.jsonl").write_text("\n".join([
            json.dumps({"timestamp": ts(6), "type": "session_meta", "payload": {"cwd": "/repo"}}),
            json.dumps({"timestamp": ts(5), "type": "event_msg", "payload": {"type": "token_count",
                        "info": {"last_token_usage": {"input_tokens": 500, "cached_input_tokens": 400,
                                                      "output_tokens": 7}}}})]) + "\n")
        self.start_at("T-2", 10, session=None)
        self.run_meter("stop", "T-2")
        stop = json.loads(self.meter.read_text().splitlines()[-1])
        self.assertEqual(stop["requests"], 2)
        self.assertEqual(stop["usage"]["codex"], {"input": 100, "cache_read": 400,
                                                  "cache_write": 0, "output": 7})

    def test_start_stop_cli_round_trip(self):
        self.assertIn("T-3 started", self.run_meter("start", "T-3", "--tier", "direct",
                                                    "--budget", "1.5M", "--session", "zz"))
        self.assertIn("already started", self.run_meter("start", "T-3", code=1))
        self.assertIn("T-3 stopped: 0 tokens", self.run_meter("stop", "T-3"))
        self.assertIn("no open start", self.run_meter("stop", "T-3", code=1))
        start = json.loads(self.meter.read_text().splitlines()[0])
        self.assertEqual(start["budget"], 1500000)

    def test_bad_budget_is_refused(self):
        self.assertIn("not a token count", self.run_meter("start", "T-4", "--budget", "lots", code=1))

    def test_outlier_needs_a_retrospective(self):
        for i, total in enumerate([100, 120, 110]):
            self.stop_event(f"T-{i}", total)
        self.stop_event("T-big", 1000)
        out = self.run_meter("report", "--check", code=1)
        self.assertIn("T-big [slice] 1k tokens", out)
        self.assertIn("OUTLIER (tier median 110)", out)
        self.assertIn("E-retro: T-big", out)
        self.run_meter("note", "T-big", "--retro", "explored code; fix: add sync model to KB")
        self.assertIn("retro: explored code", self.run_meter("report", "--check"))

    def test_tiers_are_compared_separately(self):
        for i in range(3):
            self.stop_event(f"T-d{i}", 100, tier="direct")
        self.stop_event("T-full", 1000, tier="full")
        self.assertNotIn("OUTLIER", self.run_meter("report", "--check"))

    def test_report_joins_ledger_quality(self):
        self.stop_event("T-q", 100)
        ledger = self.root / "ledger.json"
        ledger.write_text(json.dumps({"feedback": [{"task": "T-q", "events": [
            {"at": ts(5), "result": "failed"}, {"at": ts(2), "result": "accepted"}]}]}))
        out = self.run_meter("report", "--ledger", str(ledger))
        self.assertIn("first result failed, 1 failed, accepted after", out)


if __name__ == "__main__":
    unittest.main()
