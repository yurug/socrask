#!/usr/bin/env python3
"""Vendoring provenance, upgrade path and adoption levels for kit-adopt.py."""
from datetime import date, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
FEATURES = {"version": 1, "features": {
    "kb-routing": {"level": "essential", "since": "v0.1.0", "tools": ["kb-lint.py"], "summary": "kb"},
    "roadmap": {"level": "triggered", "since": "v0.2.0", "tools": ["roadmap-check.py"], "trigger": "multi-slice"},
    "metrics": {"level": "optional", "since": "v0.1.0", "tools": [], "summary": "m"}}}


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True, env=ENV).stdout.strip()


class KitAdoptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.kit, self.proj = root / "kit", root / "proj"
        (self.kit / "tools").mkdir(parents=True)
        (self.kit / "skills/spec-driven-dev").mkdir(parents=True)
        shutil.copy(HERE / "kit-adopt.py", self.kit / "tools/kit-adopt.py")
        (self.kit / "tools/kit-features.json").write_text(json.dumps(FEATURES))
        (self.kit / "skills/spec-driven-dev/kb-lint.py").write_text("print('lint v1')\n")
        git(root, "init", "-q", str(self.kit))
        git(self.kit, "add", ".")
        git(self.kit, "commit", "-qm", "v1")
        git(self.kit, "tag", "v0.1.0")
        self.proj.mkdir()

    def release(self, tag, text):
        (self.kit / "skills/spec-driven-dev/kb-lint.py").write_text(text)
        (self.kit / "tools/roadmap-check.py").write_text("print('roadmap')\n")
        git(self.kit, "add", ".")
        git(self.kit, "commit", "-qm", tag)
        git(self.kit, "tag", tag)

    def run_tool(self, *args, code=0):
        out = subprocess.run([sys.executable, str(self.kit / "tools/kit-adopt.py"), *args],
                             cwd=self.proj, capture_output=True, text=True, timeout=20, env=ENV)
        self.assertEqual(out.returncode, code, out.stdout + out.stderr)
        return out.stdout + out.stderr

    def adoption(self, features, tag="v0.1.0"):
        (self.proj / "kb/work").mkdir(parents=True, exist_ok=True)
        (self.proj / "kb/work/adoption.json").write_text(json.dumps({"kit_tag": tag, "features": features}))

    def test_vendor_pins_and_check_detects_local_edits(self):
        self.assertIn("pinned v0.1.0", self.run_tool("vendor", "kb-lint.py"))
        manifest = json.loads((self.proj / "tools/socrask.json").read_text())
        self.assertEqual(manifest["files"]["tools/kb-lint.py"]["source"], "skills/spec-driven-dev/kb-lint.py")
        self.run_tool("check")
        (self.proj / "tools/kb-lint.py").write_text("print('patched')\n")
        self.assertIn("E-integrity: tools/kb-lint.py differs", self.run_tool("check", code=1))

    def test_status_shows_upstream_changes_and_new_features_then_upgrade(self):
        self.run_tool("vendor", "kb-lint.py")
        self.release("v0.2.0", "print('lint v2')\n")
        out = self.run_tool("status")
        self.assertIn("pinned v0.1.0; latest release v0.2.0", out)
        self.assertIn("changed upstream: tools/kb-lint.py", out)
        self.assertIn("new triggered feature roadmap (v0.2.0): multi-slice", out)
        self.run_tool("upgrade")
        self.assertEqual((self.proj / "tools/kb-lint.py").read_text(), "print('lint v2')\n")
        self.adoption({"kb-routing": {"state": "adopted"}}, tag="v0.2.0")
        self.assertIn("W-unrecorded: triggered feature roadmap", self.run_tool("check"))

    def test_legacy_manifest_is_refused(self):
        (self.proj / "tools").mkdir()
        (self.proj / "tools/agentic-dev-kit.json").write_text("{}")
        self.assertIn("E-legacy", self.run_tool("check", code=1))

    def test_adoption_levels(self):
        self.run_tool("vendor", "kb-lint.py")
        self.adoption({"kb-routing": {"state": "not-applicable", "reason": "no KB"},
                       "roadmap": {"state": "not-applicable"}})
        out = self.run_tool("check", code=1)
        self.assertIn("kb-routing is essential; adopt it or defer it", out)
        self.assertIn("roadmap not-applicable needs the reason", out)
        self.adoption({"kb-routing": {"state": "adopted"},
                       "roadmap": {"state": "not-applicable", "reason": "single slice so far"}})
        self.assertIn("0 errors, 0 warnings", self.run_tool("check"))

    def test_deferred_needs_task_and_is_revisited(self):
        self.run_tool("vendor", "kb-lint.py")
        self.adoption({"kb-routing": {"state": "deferred"}, "roadmap": {"state": "not-applicable", "reason": "r"}})
        self.assertIn("deferred needs task and review_on", self.run_tool("check", code=1))
        past = (date.today() - timedelta(days=1)).isoformat()
        self.adoption({"kb-routing": {"state": "deferred", "task": "T-1", "review_on": past},
                       "roadmap": {"state": "not-applicable", "reason": "r"}})
        self.assertIn("W-revisit: kb-routing", self.run_tool("check"))

    def test_adopted_feature_needs_its_tools_and_versions_must_agree(self):
        self.run_tool("vendor", "kb-lint.py")
        self.adoption({"kb-routing": {"state": "adopted"}, "roadmap": {"state": "adopted"}}, tag="v0.0.9")
        out = self.run_tool("check", code=1)
        self.assertIn("roadmap adopted but roadmap-check.py not vendored", out)
        self.assertIn("E-version", out)

    def test_real_catalogue_names_only_shipped_tools(self):
        kit = HERE.parent
        for fid, f in json.loads((HERE / "kit-features.json").read_text())["features"].items():
            self.assertIn(f["level"], ("essential", "triggered", "optional"), fid)
            self.assertTrue(f.get("trigger") if f["level"] == "triggered" else True, fid)
            for tool in f["tools"]:
                self.assertTrue((kit / "tools" / tool).is_file() or
                                (kit / "skills/spec-driven-dev" / tool).is_file(), f"{fid}: {tool}")

    def test_dirty_kit_refuses_to_vendor(self):
        (self.kit / "skills/spec-driven-dev/kb-lint.py").write_text("dirty\n")
        self.assertIn("local changes", self.run_tool("vendor", "kb-lint.py", code=2))


if __name__ == "__main__":
    unittest.main()
