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
        self.root = Path(self.temp.name)/'source'
        self.root.mkdir()
        (self.root/'tools').mkdir()
        for name in ['spec-driven-dev', 'another-skill']:
            skill = self.root/'skills'/name
            skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('---\nname: '+name+'\ndescription: test\n---\n')
        shutil.copyfile(Path(__file__).with_name('sync-skills.py'), self.root/'tools/sync-skills.py')
        self.claude, self.codex = Path(self.temp.name)/'claude', Path(self.temp.name)/'codex'

    def call(self, *args):
        return subprocess.run([sys.executable, str(self.root/'tools/sync-skills.py'),
            '--claude-dir', str(self.claude), '--codex-dir', str(self.codex), *args], capture_output=True, text=True)

    def pin_source(self):
        """Use an actual Git repository; revision claims must survive source changes."""
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()
        git('init', '-q')
        git('add', 'skills', 'tools')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
            'commit', '-qm', 'Reviewed source')
        return git('rev-parse', 'HEAD')

    def test_revision_bound_install_and_check(self):
        pin = self.pin_source()
        self.assertEqual(self.call('--target', 'both', '--expected-revision', pin).returncode, 0)
        self.assertEqual(self.call('--target', 'both', '--expected-revision', pin, '--check').returncode, 0)

    def test_wrong_revision_refuses_before_install(self):
        self.pin_source()
        out = self.call('--target', 'both', '--expected-revision', '0' * 40)
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse(self.claude.exists())
        self.assertFalse(self.codex.exists())

    def test_dirty_selected_skill_refuses_even_at_matching_head(self):
        pin = self.pin_source()
        (self.root/'skills/spec-driven-dev/SKILL.md').write_text('unreviewed change')
        self.assertNotEqual(self.call('--only', 'spec-driven-dev', '--expected-revision', pin).returncode, 0)
        self.assertFalse(self.claude.exists())

    def test_new_selected_reference_refuses(self):
        pin = self.pin_source()
        (self.root/'skills/spec-driven-dev/new-reference.md').write_text('unreviewed rules')
        self.assertNotEqual(self.call('--only', 'spec-driven-dev', '--expected-revision', pin).returncode, 0)
        self.assertFalse(self.claude.exists())

    def test_other_kit_changes_invalidate_revision_claim(self):
        pin = self.pin_source()
        (self.root/'skills/another-skill/SKILL.md').write_text('unrelated work')
        self.assertNotEqual(self.call('--only', 'spec-driven-dev', '--expected-revision', pin).returncode, 0)
        self.assertFalse(self.claude.exists())

    def test_empty_revision_cannot_disable_requested_verification(self):
        self.pin_source()
        out = self.call('--target', 'both', '--expected-revision', '')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('full lowercase 40-character', out.stderr)
        self.assertFalse(self.claude.exists())

    def test_shared_instructions_change_refuses(self):
        (self.root/'docs').mkdir()
        shared = self.root/'docs/agent-adoption.md'
        shared.write_text('reviewed shared instructions')
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', 'docs'], check=True)
        pin = self.pin_source()
        shared.write_text('changed shared instructions')
        out = self.call('--only', 'spec-driven-dev', '--expected-revision', pin)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('kit source differs', out.stderr)
        self.assertFalse(self.claude.exists())

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

    def test_dangling_host_directory_is_preflighted_across_hosts(self):
        self.codex.symlink_to(self.root/'missing')
        self.assertNotEqual(self.call('--target','both').returncode, 0)
        self.assertFalse(self.claude.exists())
        self.assertTrue(self.codex.is_symlink())

    def test_nondirectory_ancestor_is_preflighted_across_hosts(self):
        self.codex.write_text('preserve')
        self.assertNotEqual(self.call('--target','both','--codex-dir',str(self.codex/'skills')).returncode, 0)
        self.assertFalse(self.claude.exists())
        self.assertEqual(self.codex.read_text(), 'preserve')


if __name__ == '__main__':
    unittest.main()
