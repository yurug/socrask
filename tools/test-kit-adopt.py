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

    def test_partial_vendor_cannot_relabel_old_files_as_the_new_release(self):
        self.run_tool('vendor', 'kb-lint.py')
        before = (self.proj / 'tools/socrask.json').read_bytes()
        self.release('v0.2.0', "print('lint v2')\n")
        self.assertIn('run upgrade', self.run_tool('vendor', 'roadmap-check.py', code=2))
        self.assertEqual((self.proj / 'tools/socrask.json').read_bytes(), before)
        self.assertFalse((self.proj / 'tools/roadmap-check.py').exists())
        self.run_tool('upgrade')
        self.run_tool('vendor', 'roadmap-check.py')
        self.run_tool('check')

    def test_annotated_release_pins_its_commit_and_allows_adding_files(self):
        git(self.kit, 'tag', '-a', 'v0.1.1', '-m', 'annotated release')
        self.run_tool('vendor', 'kb-lint.py')
        self.run_tool('upgrade', '--to', 'v0.1.1')
        self.run_tool('vendor', 'kit-features.json')
        manifest = json.loads((self.proj / 'tools/socrask.json').read_text())
        self.assertEqual(manifest['revision'], git(self.kit, 'rev-parse', 'HEAD'))
        self.run_tool('check')

    def test_actual_ledger_installs_transitive_dependencies_and_starts(self):
        for name in ('ledger.py', 'project-check.py', 'project_history.py'):
            shutil.copy(HERE / name, self.kit / 'tools' / name)
        catalogue = dict(FEATURES, dependencies={'tools/ledger.py': ['tools/project-check.py'],
                            'tools/project-check.py': ['tools/project_history.py']})
        (self.kit / 'tools/kit-features.json').write_text(json.dumps(catalogue))
        git(self.kit, 'add', '.')
        git(self.kit, 'commit', '-qm', 'ledger tools')
        self.run_tool('vendor', 'ledger.py')
        manifest = json.loads((self.proj / 'tools/socrask.json').read_text())
        self.assertEqual(len(manifest['files']), 3)
        for entry in manifest['files'].values():
            self.assertEqual(entry['revision'], manifest['revision'])
        run = subprocess.run([sys.executable, 'tools/ledger.py', '--help'], cwd=self.proj, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.run_tool('check')
        del manifest['files']['tools/project_history.py']
        (self.proj / 'tools/socrask.json').write_text(json.dumps(manifest))
        self.assertIn('E-dependency', self.run_tool('check', code=1))

    def test_missing_source_is_detected_before_any_upgrade_write(self):
        self.run_tool('vendor', 'kb-lint.py', 'kit-features.json')
        before = {p: p.read_bytes() for p in (self.proj / 'tools').iterdir()}
        self.release('v0.2.0', "print('v2')\n")
        catalogue = dict(FEATURES, dependencies={'skills/spec-driven-dev/kb-lint.py': ['tools/missing.py']})
        (self.kit / 'tools/kit-features.json').write_text(json.dumps(catalogue))
        git(self.kit, 'add', '.')
        git(self.kit, 'commit', '-qm', 'broken dependency')
        self.run_tool('upgrade', '--to', 'HEAD', code=2)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_legacy_provenance_needs_full_upgrade_and_local_edits_survive(self):
        self.run_tool('vendor', 'kb-lint.py')
        path = self.proj / 'tools/socrask.json'
        manifest = json.loads(path.read_text())
        del manifest['files']['tools/kb-lint.py']['revision']
        path.write_text(json.dumps(manifest))
        self.assertIn('E-provenance', self.run_tool('check', code=1))
        self.run_tool('upgrade')
        self.run_tool('check')
        script = self.proj / 'tools/kb-lint.py'
        script.write_text('local change\n')
        self.assertIn('local edits', self.run_tool('upgrade', code=2))
        self.assertEqual(script.read_text(), 'local change\n')


if __name__ == "__main__":
    unittest.main()
