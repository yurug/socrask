#!/usr/bin/env python3
"""Source declaration, exposure, cadence and digest checks for source-check.py."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECK = Path(__file__).with_name("source-check.py")
SOURCE = {"id": "S-slack", "kind": "slack", "locator": "#proj-dev", "owner": "alice",
          "via": "slack MCP", "cadence_days": 1, "visibility": "internal",
          "cursor": "1729500000.0001", "last_synced": "2026-10-20"}
DIGEST = """---
id: digest-s-slack-2026-10-20
type: external
summary: Sync of #proj-dev on 2026-10-20.
domain: sources
last-updated: 2026-10-20
---
# S-slack, 2026-10-20

| Item | Link | Disposition | Ref |
|---|---|---|---|
| export is slow | https://slack/p1 | feedback | F-7 |
| team picked Postgres | https://slack/p2 | fact | kb/spec/storage.md |
| should retries be capped? | https://slack/p3 | question | forebrief:card-3 |
| lunch plans | https://slack/p4 | noise | |
"""


class SourceCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for d in ("kb/work", "kb/spec", "kb/sources/digests"):
            (self.root / d).mkdir(parents=True)
        (self.root / "kb/spec/storage.md").write_text("# Storage\n")
        (self.root / "kb/work/ledger.json").write_text(json.dumps({"feedback": [{"id": "F-7"}]}))
        self.digest = self.root / "kb/sources/digests/S-slack-2026-10-20.md"
        self.digest.write_text(DIGEST)

    def run_check(self, sources, *args, code=0, visibility="private", today="2026-10-20"):
        (self.root / "kb/work/sources.json").write_text(json.dumps(
            {"version": 1, "kb_visibility": visibility, "sources": sources}))
        result = subprocess.run([sys.executable, str(CHECK), "--sources",
                                 str(self.root / "kb/work/sources.json"), "--today", today, *args],
                                capture_output=True, text=True, timeout=10)
        out = result.stdout + result.stderr
        self.assertEqual(result.returncode, code, out)
        return out

    def test_synced_source_with_complete_digest_passes(self):
        self.assertIn("1 sources, 0 errors, 0 warnings", self.run_check([SOURCE]))

    def test_internal_source_cannot_feed_a_public_kb(self):
        out = self.run_check([SOURCE], code=1, visibility="public")
        self.assertIn("E-exposure: internal source S-slack feeds a public KB", out)
        public = dict(SOURCE, visibility="public")
        self.run_check([public], visibility="public")

    def test_overdue_source_warns_and_is_listed_at_session_start(self):
        out = self.run_check([SOURCE], today="2026-10-22")
        self.assertIn("W-overdue: source S-slack", out)
        due = self.run_check([SOURCE], "--due", today="2026-10-22")
        self.assertIn("Source S-slack (slack, #proj-dev) is due", due)
        self.assertEqual(self.run_check([SOURCE], "--due"), "")

    def test_missing_digest_fails(self):
        self.digest.unlink()
        self.assertIn("E-digest: source S-slack synced 2026-10-20 without", self.run_check([SOURCE], code=1))

    def test_each_disposition_ref_must_resolve(self):
        self.digest.write_text(DIGEST.replace("F-7", "F-99").replace("storage.md", "gone.md")
                               .replace("forebrief:card-3", "ask alice").replace("| noise |", "| maybe |"))
        out = self.run_check([SOURCE], code=1)
        self.assertIn("cites feedback `F-99`, absent from the ledger", out)
        self.assertIn("cites KB file `kb/spec/gone.md`", out)
        self.assertIn("needs Ref forebrief:<card-id>", out)
        self.assertIn("has disposition `maybe`", out)

    def test_schema_errors(self):
        bad = copy.deepcopy(SOURCE)
        del bad["owner"]
        bad["cadence_days"] = 0
        out = self.run_check([bad], code=1)
        self.assertIn("lacks owner", out)
        self.assertIn("positive cadence_days", out)

    def test_never_synced_source_is_due_without_digest_error(self):
        fresh = dict(SOURCE, last_synced=None)
        out = self.run_check([fresh])
        self.assertIn("W-overdue: source S-slack last synced never", out)


if __name__ == "__main__":
    unittest.main()
