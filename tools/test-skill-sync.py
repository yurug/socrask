#!/usr/bin/env python3
"""Exercise real link installation and refusal without touching either user's home."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class SkillSync(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='skill sync ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'tools').mkdir()
        for name in ['spec-driven-dev', 'another-skill']:
            skill = self.root/'skills'/name
            skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('---\nname: '+name+'\ndescription: test\n---\n')
        shutil.copyfile(Path(__file__).with_name('sync-skills.py'), self.root/'tools/sync-skills.py')
        self.claude, self.codex = self.root/'claude', self.root/'codex'

    def call(self, *args):
        return subprocess.run([sys.executable, str(self.root/'tools/sync-skills.py'),
            '--claude-dir', str(self.claude), '--codex-dir', str(self.codex), *args], capture_output=True, text=True)

    def test_both_hosts_idempotent_and_checkable(self):
        for _ in range(2):
            self.assertEqual(self.call('--target', 'both').returncode, 0)
        self.assertEqual(self.call('--target', 'both', '--check').returncode, 0)
        self.assertEqual((self.codex/'spec-driven-dev').resolve(), self.root/'skills/spec-driven-dev')

    def test_read_only_check_reports_missing_without_creation(self):
        self.assertNotEqual(self.call('--check').returncode, 0)
        self.assertFalse(self.claude.exists())

    def test_conflict_is_preflighted_before_any_other_installation(self):
        self.codex.mkdir()
        (self.codex/'spec-driven-dev').mkdir()
        (self.codex/'spec-driven-dev/keep.txt').write_text('keep')
        self.assertNotEqual(self.call('--target','both').returncode, 0)
        self.assertFalse(self.claude.exists())
        self.assertEqual((self.codex/'spec-driven-dev/keep.txt').read_text(), 'keep')

    def test_foreign_broken_links_require_explicit_replacement(self):
        self.claude.mkdir()
        dst = self.claude/'spec-driven-dev'
        dst.symlink_to(self.root/'missing')
        self.assertNotEqual(self.call('--only','spec-driven-dev').returncode, 0)
        self.assertEqual(self.call('--only','spec-driven-dev','--replace-links').returncode, 0)
        self.assertFalse((self.claude/'another-skill').exists())

    def test_unknown_selection_never_creates_destinations(self):
        self.assertEqual(self.call('--only','../unknown').returncode, 2)
        self.assertFalse(self.claude.exists())


if __name__ == '__main__':
    unittest.main()
