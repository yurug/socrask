#!/usr/bin/env python3
"""Routing cases for memory-route.py."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).with_name("memory-route.py")


class MemoryRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.project = base / "project"
        (self.project / "kb").mkdir(parents=True)
        (self.project / "kb" / "INDEX.md").write_text("# KB\n")
        self.memory = base / ".claude" / "projects" / "-project" / "memory"
        self.memory.mkdir(parents=True)

    def run_hook(self, name, body, cwd=None):
        target = self.memory / name
        target.write_text(body)
        event = {"tool_name": "Write", "tool_input": {"file_path": str(target)},
                 "cwd": str(cwd or self.project / "src")}
        result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_feedback_memory_in_a_kb_project_is_routed(self):
        out = self.run_hook("no-leak.md", "---\nname: no-leak\nmetadata:\n  type: feedback\n---\nRule.\n")
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("kb/conventions/method.md", context)
        self.assertIn("`feedback`", context)

    def test_user_memory_stays_silent(self):
        self.assertEqual(self.run_hook("prefs.md", "---\nname: prefs\ntype: user\n---\nTerse.\n"), "")

    def test_project_without_kb_stays_silent(self):
        out = self.run_hook("rule.md", "---\ntype: project\n---\nRule.\n", cwd=Path(self.temp.name))
        self.assertEqual(out, "")

    def test_index_and_non_memory_files_stay_silent(self):
        self.assertEqual(self.run_hook("MEMORY.md", "- type: feedback\n"), "")
        event = {"tool_input": {"file_path": str(self.project / "kb" / "INDEX.md")},
                 "cwd": str(self.project)}
        result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stdout, "")

    def test_malformed_input_stays_silent(self):
        result = subprocess.run([sys.executable, str(HOOK)], input="not json",
                                capture_output=True, text=True, timeout=10)
        self.assertEqual((result.returncode, result.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
