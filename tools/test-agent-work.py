#!/usr/bin/env python3
"""Exercise coordination using real Git worktrees and competing processes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

TOOL = str(Path(__file__).with_name('agent-work.py'))


class WorkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.git('init', '-q', str(self.repo), cwd=self.root)
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.repo / 'seed').write_text('seed')
        self.git('add', 'seed')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').stdout.strip()
        self.w1, self.w2 = self.root / 'one', self.root / 'two'
        for branch, path in [('one', self.w1), ('two', self.w2)]:
            self.git('worktree', 'add', '-qb', branch, str(path))
        self.record = self.root / 'alignment.json'
        self.record.write_text(json.dumps({'version': 1, 'work_id': 'lead', 'tier': 'slice', 'base': self.base,
            'checkpoints': {'inbrief': {'status': 'not-required', 'reason': 'Same known architecture and scope'},
                            'backbrief': {'status': 'required', 'reason': 'Review combined changes with owner'}}}))
        self.claim(self.repo, 'lead', 'docs', coordinator=True)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.repo, text=True, capture_output=True, check=True)

    def invoke(self, cwd, *args):
        return subprocess.run([sys.executable, TOOL, *args], cwd=cwd, text=True, capture_output=True)

    def claim_args(self, task, path, coordinator=False):
        return ['claim', '--task', task, '--owner', task, '--path', path, '--criteria', 'Meaningful fixture acceptance',
            *(['--alignment', str(self.record)] if coordinator else ['--role', 'worker', '--coordinator', 'lead'])]

    def claim(self, cwd, task, path, coordinator=False):
        r = self.invoke(cwd, *self.claim_args(task, path, coordinator))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_simultaneous_overlapping_claims(self):
        procs = [subprocess.Popen([sys.executable, TOOL, *self.claim_args(t, 'src')], cwd=w,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for t, w in [('a', self.w1), ('b', self.w2)]]
        results = []
        for proc in procs:
            proc.communicate(timeout=10)
            results.append(proc.returncode)
        self.assertEqual(sorted(results), [0, 2])

    def test_independent_paths_and_scope(self):
        self.claim(self.w1, 'a', 'src/a')
        self.claim(self.w2, 'b', 'src/b')
        r = self.invoke(self.w2, *self.claim_args('c', 'elsewhere'))
        self.assertEqual(r.returncode, 2)  # no second writer in one tree
        (self.w1 / 'outside').write_text('unowned')
        r = self.invoke(self.w1, 'check', '--task', 'a', '--owner', 'a')
        self.assertEqual(r.returncode, 2)
        self.assertIn('outside', r.stderr)

    def test_resource_exclusion_and_release(self):
        self.claim(self.w1, 'a', 'src/a')
        self.claim(self.w2, 'b', 'src/b')
        marker = self.root / 'started'
        proc = subprocess.Popen([sys.executable, TOOL, 'run', '--task', 'a', '--owner', 'a', '--resource', 'browser', '--',
            sys.executable, '-c', f'from pathlib import Path; import time; Path({str(marker)!r}).touch(); time.sleep(1)'], cwd=self.w1,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if marker.exists():
                    break
                time.sleep(.02)
            self.assertTrue(marker.exists())
            r = self.invoke(self.w2, 'run', '--task', 'b', '--owner', 'b', '--resource', 'browser', '--', 'true')
            self.assertEqual(r.returncode, 2)
            r = self.invoke(self.w2, 'run', '--task', 'b', '--owner', 'b', '--resource', 'other', '--', 'true')
            self.assertEqual(r.returncode, 0, r.stderr)
            proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0)
            r = self.invoke(self.w2, 'run', '--task', 'b', '--owner', 'b', '--resource', 'browser', '--', 'false')
            self.assertEqual(r.returncode, 1)
            state = json.loads(self.invoke(self.repo, 'status').stdout)
            self.assertEqual(state['resources'], {})
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()

    def test_handoff_needs_current_clean_success_and_human_close(self):
        r = self.invoke(self.repo, 'handoff', '--task', 'lead', '--owner', 'lead')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.invoke(self.repo, 'run', '--task', 'lead', '--owner', 'lead', '--', 'true').returncode, 0)
        self.assertEqual(self.invoke(self.repo, 'handoff', '--task', 'lead', '--owner', 'lead').returncode, 0)
        r = self.invoke(self.repo, 'close', '--task', 'lead', '--owner', 'lead', '--outcome', 'integrated',
                        '--reason', 'All integration evidence inspected', '--alignment', str(self.record))
        self.assertEqual(r.returncode, 2)
        self.assertIn('alignment', r.stderr)

    def test_dirty_or_changed_head_cannot_reuse_evidence(self):
        self.claim(self.w1, 'a', 'src')
        (self.w1 / 'src').mkdir()
        (self.w1 / 'src/a').write_text('change')
        self.assertEqual(self.invoke(self.w1, 'run', '--task', 'a', '--owner', 'a', '--', 'true').returncode, 0)
        self.git('add', 'src', cwd=self.w1)
        self.git('commit', '-qm', 'change', cwd=self.w1)
        self.assertEqual(self.invoke(self.w1, 'handoff', '--task', 'a', '--owner', 'a').returncode, 2)
        self.assertEqual(self.invoke(self.w1, 'run', '--task', 'a', '--owner', 'a', '--', 'true').returncode, 0)
        self.assertEqual(self.invoke(self.w1, 'handoff', '--task', 'a', '--owner', 'a').returncode, 0)

    def test_rename_does_not_hide_unowned_source(self):
        self.claim(self.w1, 'a', 'owned')
        self.git('mv', 'seed', 'owned', cwd=self.w1)
        self.git('commit', '-qm', 'rename', cwd=self.w1)
        r = self.invoke(self.w1, 'check', '--task', 'a', '--owner', 'a')
        self.assertEqual(r.returncode, 2)
        self.assertIn('seed', r.stderr)

    def test_combined_integration_and_stale_closure(self):
        self.claim(self.w1, 'a', 'src')
        (self.w1 / 'src').write_text('worker code')
        self.git('add', 'src', cwd=self.w1)
        self.git('commit', '-qm', 'worker', cwd=self.w1)
        self.assertEqual(self.invoke(self.w1, 'run', '--task', 'a', '--owner', 'a', '--', 'true').returncode, 0)
        self.assertEqual(self.invoke(self.w1, 'handoff', '--task', 'a', '--owner', 'a').returncode, 0)
        self.git('merge', '--ff-only', 'one')
        self.assertEqual(self.invoke(self.repo, 'run', '--task', 'lead', '--owner', 'lead', '--', 'true').returncode, 0)
        self.assertEqual(self.invoke(self.repo, 'handoff', '--task', 'lead', '--owner', 'lead').returncode, 0)
        record = json.loads(self.record.read_text())
        record['head'] = self.git('rev-parse', 'HEAD').stdout.strip()
        record['checkpoints']['backbrief'] = {'status': 'human-complete', 'reason': 'Synthetic test fixture only',
            'evidence': {'kind': 'human-event', 'ref': 'fixture:human-completion'}}
        self.record.write_text(json.dumps(record))
        close = ['close', '--task', 'lead', '--owner', 'lead', '--outcome', 'integrated',
                 '--reason', 'Integration and fixture evidence complete', '--alignment', str(self.record)]
        for bad_field, bad_value in [('tier', 'direct'), ('work_id', 'different-task')]:
            wrong = dict(record, **{bad_field: bad_value})
            self.record.write_text(json.dumps(wrong))
            self.assertEqual(self.invoke(self.repo, *close).returncode, 2)
        self.record.write_text(json.dumps(record))
        (self.repo / 'docs').write_text('unreviewed')
        self.assertEqual(self.invoke(self.repo, *close).returncode, 2)
        (self.repo / 'docs').unlink()
        self.assertEqual(self.invoke(self.repo, *close).returncode, 0)
        self.assertEqual(self.invoke(self.w1, 'close', '--task', 'a', '--owner', 'a', '--outcome', 'integrated',
                                    '--reason', 'Included in coordinator tested commit').returncode, 0)

    def test_background_descendant_keeps_resource(self):
        self.claim(self.w1, 'a', 'src/a')
        self.claim(self.w2, 'b', 'src/b')
        r = self.invoke(self.w1, 'run', '--task', 'a', '--owner', 'a', '--resource', 'browser', '--',
                        'sh', '-c', 'sleep 2 </dev/null >/dev/null 2>&1 &')
        self.assertEqual(r.returncode, 2)
        self.assertIn('descendants', r.stderr)
        self.assertEqual(self.invoke(self.w2, 'run', '--task', 'b', '--owner', 'b', '--resource', 'browser', '--', 'true').returncode, 2)

    def test_failed_lease_persistence_never_executes_payload(self):
        self.claim(self.w1, 'a', 'src')
        marker = self.root / 'must-not-run'
        argv = [TOOL, 'run', '--task', 'a', '--owner', 'a', '--resource', 'shared', '--',
                sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()']
        source = f"""import importlib.util,sys
spec=importlib.util.spec_from_file_location('work',{TOOL!r})
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def failed_write(*args): raise OSError('injected persistence failure')
module.write=failed_write
sys.argv={argv!r}
module.main()
"""
        r = subprocess.run([sys.executable, '-c', source], cwd=self.w1, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(marker.exists())

    def test_missing_alignment_and_path_escape_fail(self):
        args = self.claim_args('other', 'src', coordinator=True)
        args[-1] = str(self.root / 'missing')
        self.assertEqual(self.invoke(self.w1, *args).returncode, 2)
        for path in ('../outside', '/etc', '.', 'src/*', '.git/config'):
            self.assertEqual(self.invoke(self.w1, *self.claim_args('escape', path)).returncode, 2)


if __name__ == '__main__':
    unittest.main()
