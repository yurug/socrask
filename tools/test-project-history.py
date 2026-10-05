#!/usr/bin/env python3
"""T-PM-HISTORY exercises actual Git graphs; fixtures do not prove user outcomes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


TOOL = Path(__file__).with_name('project-check.py')
FIXTURES = runpy.run_path(str(TOOL.with_name('test-project-check.py')))
LEDGER = 'kb/work/ledger.json'


def event(day=3, **fields):
    return dict(at=f'2026-10-0{day}T10:00:00Z', result='failed', ref='feedback.md', **fields)


def opened(*events):
    data = FIXTURES['fixture']()
    data['tasks'][0]['status'] = 'reopened'
    data['feedback'][0]['events'] = list(events)
    return data


class ProjectHistory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'History fixture')
        (self.root / 'feedback.md').write_text('| S32 | Keep failed observations |\n')
        (self.root / 'evidence.json').write_text('{"fixture":true}')
        (self.root / LEDGER).parent.mkdir(parents=True)
        self.base = self.commit(opened(event()))

    def git(self, *args, input=None):
        run = subprocess.run(['git', '--no-replace-objects', '-C', str(self.root), *args],
                             input=input, text=True, capture_output=True, env=self.env)
        self.assertEqual(run.returncode, 0, run.stderr)
        return run.stdout.strip()

    def write(self, data):
        (self.root / LEDGER).write_text(json.dumps(data))

    def commit(self, data=None):
        if data is not None:
            self.write(data)
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture', '--allow-empty')
        return self.git('rev-parse', 'HEAD')

    def gate(self, code=0, reason=None, base=True, env=None, ledger=None, root=None):
        args = [sys.executable, str(TOOL), '--root', str(root or self.root), '--ledger',
                str(ledger or self.root / LEDGER), '--as-of', '2026-10-04', '--summary']
        if base is not False:
            args += ['--history-base', self.base if base is True else base]
        run = subprocess.run(args, text=True, capture_output=True, env=env or self.env)
        self.assertEqual(run.returncode, code, run.stdout + run.stderr)
        self.assertNotIn('Traceback', run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['coherent'], code == 0)
        if reason:
            self.assertIn(reason, '\n'.join(result['failures']))
        return result

    def test_T_PM_HISTORY_snapshot_mode_explicitly_unchecked(self):
        self.assertEqual(self.gate(base=False)['history'], {'checked': False})

    def test_T_PM_HISTORY_deletion_cannot_make_false_closure(self):
        self.write(FIXTURES['closed_fixture']())
        self.gate(base=False)  # This is the previously exploitable coherent snapshot.
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_intermediate_commit_cannot_hide_a_failure(self):
        self.commit(opened(event(), event(4)))
        self.commit(opened(event()))
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_merge_selecting_other_branch_retains_failure(self):
        self.git('checkout', '-qb', 'failure')
        self.commit(opened(event(), event(4)))
        self.git('checkout', 'main')
        self.commit()
        self.git('merge', '-q', '--no-ff', '-s', 'ours', 'failure', '-m', 'drop side failure')
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_merge_created_event_cannot_disappear(self):
        self.git('checkout', '-qb', 'side')
        self.commit()
        self.git('checkout', 'main')
        self.commit()
        self.git('merge', '-q', '--no-ff', '--no-commit', '-s', 'ours', 'side')
        self.commit(opened(event(), event(4)))
        self.commit(opened(event()))
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_prebase_fork_merged_later_is_checked(self):
        self.git('branch', 'early')
        self.base = self.commit()
        self.git('checkout', 'early')
        self.commit(opened(event(), event(4)))
        self.git('checkout', 'main')
        self.git('merge', '-q', '--no-ff', '-s', 'ours', 'early', '-m', 'merge early fork')
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_append_interleave_and_metadata_remap_pass(self):
        early, late = event(2), event(4)
        self.base = self.commit(opened(early))
        self.git('checkout', '-qb', 'late')
        self.commit(opened(early, late))
        self.git('checkout', 'main')
        self.commit(opened(early, event()))
        self.git('merge', '-q', '--no-ff', '-s', 'ours', 'late', '-m', 'interleave later')
        data = opened(early, event(), late)
        data['tasks'][0]['id'] = data['feedback'][0]['task'] = 'T-REMAP'
        data['feedback'][0].update(owner='new-owner', disposition={'rationale': 'New plan'})
        self.write(data)
        result = self.gate()['history']
        self.assertTrue(result['checked'])
        self.assertEqual(result['trusted_base'], self.base)
        self.assertEqual(result['resolved_head'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(result['snapshot_count'], 3)
        self.assertEqual(result['current_ledger'], dict(path=LEDGER, sha256=hashlib.sha256(
            (self.root / LEDGER).read_bytes()).hexdigest()))

    def test_T_PM_HISTORY_old_review_and_missing_reference_files_do_not_expire_history(self):
        data = opened(event())
        data['tasks'][0]['review_on'] = '2020-01-01'
        data['tasks'][0]['refs'] = ['old-deleted.md']
        self.base = self.commit(data)
        self.write(opened(event()))
        self.gate()

    def test_T_PM_HISTORY_local_reference_normalization_remains_compatible(self):
        old = dict(event(), ref='old-directory/../feedback.md')
        self.base = self.commit(opened(old))
        self.gate()

    def test_T_PM_HISTORY_sha256_repository_uses_full_commit_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            original = self.root
            self.root = Path(directory)
            try:
                self.git('init', '-q', '--object-format=sha256', '-b', 'main')
                self.git('config', 'user.email', 'fixture@example.invalid')
                self.git('config', 'user.name', 'History fixture')
                (self.root / LEDGER).parent.mkdir(parents=True)
                (self.root / 'feedback.md').write_text('| S32 | request |\n')
                base = self.commit(opened(event()))
                self.assertEqual(len(base), 64)
                self.assertEqual(self.gate(base=base)['history']['trusted_base'], base)
            finally:
                self.root = original

    def test_T_PM_HISTORY_event_ref_is_structural_in_old_snapshot(self):
        # Missing old files must not mask event retention with a filesystem error.
        self.base = self.commit(opened(dict(event(), ref='old-deleted.md')))
        self.write(opened(event()))
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_removed_feedback_ID_fails_even_if_inventory_changed(self):
        data = opened()
        data['feedback'][0]['id'] = 'S33'
        (self.root / 'feedback.md').write_text('| S33 | Replacement request |\n')
        self.write(data)
        self.gate(2, 'removed feedback ID: S32')

    def test_T_PM_HISTORY_duplicate_multiplicity_is_preserved(self):
        self.base = self.commit(opened(event(), event()))
        self.write(opened(event()))
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_mutation_including_extra_fields_and_equal_time_order_fails(self):
        original = event(note='original')
        second = event(note='second')
        self.base = self.commit(opened(original, second))
        for events in ([dict(original, note='edited'), second], [second, original], [event(), second]):
            with self.subTest(events=events):
                self.write(opened(*events))
                self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_malformed_old_ledgers_fail_closed(self):
        for raw in ['{', '{"version":1,"version":1}', '{"version":NaN}',
                    '{"version":true,"feedback":[]}', '{"version":2,"feedback":[]}',
                    '{"version":1,"feedback":[{"id":"S32","events":null}]}']:
            with self.subTest(raw=raw):
                (self.root / LEDGER).write_text(raw)
                bad = self.commit()
                self.write(opened(event()))
                self.gate(2, 'history', base=bad)

    def test_T_PM_HISTORY_invalid_historical_event_shapes_fail(self):
        for events in ([None], [dict(event(), at='2026-10-03')], [dict(event(), result='maybe')],
                       [dict(event(), ref='../outside')], [event(4), event()],
                       [dict(event(), ref=None)]):
            data = opened(*events)
            bad = self.commit(data)
            self.write(opened(event()))
            self.gate(2, 'history', base=bad)
        data = opened(event())
        data['feedback'].append(copy.deepcopy(data['feedback'][0]))
        bad = self.commit(data)
        self.write(opened(event()))
        self.gate(2, 'duplicate feedback ID', base=bad)

    def test_T_PM_HISTORY_missing_short_noncommit_and_nonancestor_base_fail(self):
        for base in ('', 'HEAD', self.base[:12], 'f' * 40, self.git('rev-parse', f'{self.base}:{LEDGER}')):
            with self.subTest(base=base):
                self.gate(2, 'history', base=base)
        self.git('checkout', '--orphan', 'unrelated')
        # Distinct content prevents identical root commits within one clock second.
        unrelated = self.commit(opened(event(4)))
        self.git('checkout', 'main')
        self.gate(2, 'ancestor', base=unrelated)

    def test_T_PM_HISTORY_base_requires_ledger_at_selected_path(self):
        (self.root / LEDGER).unlink()
        self.base = self.commit()
        self.write(opened(event()))
        self.gate(2, 'ledger missing at trusted base')

    def test_T_PM_HISTORY_pre_adoption_branch_without_ledger_is_skipped(self):
        (self.root / LEDGER).unlink()
        self.commit()
        self.git('branch', 'pre-adoption')
        self.base = self.commit(opened(event()))
        self.git('checkout', 'pre-adoption')
        self.commit()
        self.git('checkout', 'main')
        self.git('merge', '-q', '--no-ff', '-s', 'ours', 'pre-adoption', '-m', 'old branch')
        self.gate()

    def test_T_PM_HISTORY_inherited_git_environment_cannot_redirect_reads(self):
        poisoned = dict(self.env, GIT_DIR='/does-not-exist', GIT_WORK_TREE='/does-not-exist',
                        GIT_COMMON_DIR='/does-not-exist', GIT_INDEX_FILE='/does-not-exist',
                        GIT_OBJECT_DIRECTORY='/does-not-exist', GIT_ALTERNATE_OBJECT_DIRECTORIES='/does-not-exist',
                        GIT_SHALLOW_FILE='/does-not-exist', GIT_CONFIG_COUNT='1',
                        GIT_CONFIG_KEY_0='core.bare', GIT_CONFIG_VALUE_0='true')
        self.gate(env=poisoned)

    def test_T_PM_HISTORY_replace_refs_cannot_erase_original_observations(self):
        # An unchecked replacement would make the baseline look like the false closure.
        self.write(FIXTURES['closed_fixture']())
        replacement = self.commit()
        self.git('replace', self.base, replacement)
        self.gate(2, 'removed, changed or reordered event')

    def test_T_PM_HISTORY_shallow_and_grafts_are_rejected(self):
        (self.root / '.git/shallow').write_text(self.base + '\n')
        self.gate(2, 'shallow')
        (self.root / '.git/shallow').unlink()
        (self.root / '.git/info/grafts').write_text(self.base + '\n')
        self.gate(2, 'grafts')

    def test_T_PM_HISTORY_missing_historical_blob_fails_closed(self):
        blob = self.git('rev-parse', f'{self.base}:{LEDGER}')
        self.commit(opened(event(), event(4)))
        (self.root / '.git/objects' / blob[:2] / blob[2:]).unlink()
        self.gate(2, 'history')

    def test_T_PM_HISTORY_nonrepository_and_outside_ledger_fail(self):
        with tempfile.TemporaryDirectory() as other:
            other = Path(other)
            (other / 'feedback.md').write_text('| S32 | request |\n')
            self.write(opened(event()))
            target = other / 'ledger.json'
            target.write_bytes((self.root / LEDGER).read_bytes())
            self.gate(2, 'history', root=other, ledger=target)
            self.gate(2, 'outside root', ledger=target)


if __name__ == '__main__':
    unittest.main()
