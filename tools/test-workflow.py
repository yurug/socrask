#!/usr/bin/env python3
"""Exercise installed tools together against real repositories and a local remote."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(os.environ, GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
           GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')


def run(cwd, *args, code=0):
    p = subprocess.run(args, cwd=cwd, env=ENV, text=True, capture_output=True, timeout=30)
    if p.returncode != code:
        raise AssertionError(f'{args}: {p.returncode} != {code}\n{p.stdout}\n{p.stderr}')
    return p.stdout + p.stderr


def git(cwd, *args):
    return run(cwd, 'git', *args).strip()


class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp = tempfile.TemporaryDirectory()
        cls.kit = Path(cls.source_temp.name)
        (cls.kit / 'tools').mkdir()
        for name in ('kit-adopt.py', 'kit-features.json', 'team-work.py', 'agent-work.py',
                     'alignment-check.py', 'ledger.py', 'project-check.py', 'project_history.py'):
            shutil.copy2(ROOT / 'tools' / name, cls.kit / 'tools' / name)
        git(cls.kit, 'init', '-q')
        git(cls.kit, 'add', '.')
        git(cls.kit, 'commit', '-qm', 'kit fixture')
        git(cls.kit, 'tag', 'v0.30.0')

    @classmethod
    def tearDownClass(cls):
        cls.source_temp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote, self.repo = self.root / 'remote.git', self.root / 'project'
        git(self.root, 'init', '-q', '--bare', '-b', 'main', str(self.remote))
        git(self.root, 'clone', '-q', str(self.remote), str(self.repo))
        run(self.repo, sys.executable, str(self.kit / 'tools/kit-adopt.py'), 'vendor', 'team-work.py', 'ledger.py')
        self.revision = json.loads((self.repo / 'tools/socrask.json').read_text())['revision']
        (self.repo / 'kb/work').mkdir(parents=True)
        (self.repo / 'kb/work/kit-revision').write_text(self.revision + '\n')
        (self.repo / '.gitignore').write_text('__pycache__/\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'install')
        git(self.repo, 'push', '-q', 'origin', 'main')
        self.base = git(self.repo, 'rev-parse', 'HEAD')
        self.record = self.root / 'alignment.json'
        self.record.write_text(json.dumps(dict(version=1, work_id='L', tier='direct', base=self.base,
            checkpoints={k:dict(status='not-required', reason='Bounded fixture change') for k in ('inbrief','backbrief')})))

    def team(self, *args, code=0):
        return run(self.repo, sys.executable, 'tools/team-work.py', *args, code=code)

    def local(self, *args, code=0):
        return run(self.repo, sys.executable, 'tools/agent-work.py', *args, code=code)

    def claim_team(self, hours='4'):
        self.team('claim', '--task', 'T', '--engineer', 'alice', '--path', 'src', '--criteria', 'Fixture passes', '--lease-hours', hours)

    def claim_local(self, path='src', code=0):
        return self.local('claim', '--task', 'L', '--owner', 'worker', '--path', path,
                          '--criteria', 'Fixture passes', '--team-task', 'T', '--alignment', str(self.record), code=code)

    def test_install_claim_test_and_handoff(self):
        self.claim_team()
        self.claim_local()
        (self.repo / 'src').mkdir()
        (self.repo / 'src/result').write_text('delivered')
        git(self.repo, 'add', 'src'); git(self.repo, 'commit', '-qm', 'deliver')
        self.local('run', '--task', 'L', '--owner', 'worker', '--', sys.executable, '-c',
                   "from pathlib import Path; assert Path('src/result').read_text() == 'delivered'")
        self.local('handoff', '--task', 'L', '--owner', 'worker')
        self.team('--ci-status-cmd', 'printf success', 'handoff', '--task', 'T', '--engineer', 'alice', '--pr', 'fixture:pr')
        record = json.loads(self.record.read_text()); record['head'] = git(self.repo, 'rev-parse', 'HEAD')
        self.record.write_text(json.dumps(record))
        self.local('close', '--task', 'L', '--owner', 'worker', '--outcome', 'integrated', '--reason',
                   'Fixture acceptance verified', '--alignment', str(self.record))
        git(self.repo, 'push', '-q', 'origin', 'main')
        self.team('close', '--task', 'T', '--engineer', 'alice', '--outcome', 'integrated', '--reason', 'Fixture accepted and merged')
        self.assertEqual(json.loads(self.local('status'))['tasks']['L']['status'], 'closed')

    def test_expired_parent_cannot_grant_local_work(self):
        self.claim_team('-1')
        self.team('claim', '--task', 'B', '--engineer', 'bob', '--path', 'src', '--criteria', 'Fixture passes')
        self.assertIn('expired', self.claim_local(code=2))
        self.assertEqual(json.loads(self.local('status'))['tasks'], {})

    def test_disconnect_expiry_and_takeover_revoke_execution_and_handoff(self):
        self.claim_team(); self.claim_local()
        self.local('run', '--task', 'L', '--owner', 'worker', '--', 'true')
        git(self.repo, 'remote', 'set-url', 'origin', str(self.root / 'absent'))
        self.assertIn('cannot refresh', self.local('run', '--task', 'L', '--owner', 'worker', '--', 'true', code=2))
        self.local('handoff', '--task', 'L', '--owner', 'worker', code=2)
        git(self.repo, 'remote', 'set-url', 'origin', str(self.remote))
        self.team('renew', '--task', 'T', '--engineer', 'alice', '--lease-hours', '-1')
        self.assertIn('expired', self.local('run', '--task', 'L', '--owner', 'worker', '--', 'true', code=2))
        self.team('takeover', '--task', 'T', '--engineer', 'bob', '--reason', 'Alice relinquished fixture work')
        self.assertIn('changed ownership', self.local('handoff', '--task', 'L', '--owner', 'worker', code=2))

    def test_expiry_during_command_invalidates_evidence_and_releases_resources(self):
        self.claim_team(); self.claim_local()
        self.local('run', '--task', 'L', '--owner', 'worker', '--resource', 'fixture', '--',
                   sys.executable, 'tools/team-work.py', 'renew', '--task', 'T', '--engineer', 'alice', '--lease-hours', '-1', code=2)
        state = json.loads(self.local('status'))
        self.assertEqual(state['resources'], {})
        self.assertIsNone(state['tasks']['L']['checks'][-1]['commit'])
        self.assertEqual(state['tasks']['L']['checks'][-1]['exit'], 2)

    def test_worker_inherits_team_binding(self):
        self.claim_team(); self.claim_local('src/lead')
        worker = self.root / 'worker'
        git(self.repo, 'worktree', 'add', '-qb', 'worker', str(worker))
        run(worker, sys.executable, 'tools/agent-work.py', 'claim', '--task', 'W', '--owner', 'w',
            '--path', 'src/worker', '--criteria', 'Fixture passes', '--role', 'worker', '--coordinator', 'L')
        state = json.loads(self.local('status'))
        self.assertEqual(state['tasks']['L']['team'], state['tasks']['W']['team'])
        self.team('renew', '--task', 'T', '--engineer', 'alice', '--lease-hours', '-1')
        run(worker, sys.executable, 'tools/agent-work.py', 'run', '--task', 'W', '--owner', 'w', '--', 'true', code=2)

    def test_custom_destination_keeps_manifest_provenance(self):
        other = self.root / 'custom'; other.mkdir()
        git(other, 'init', '-q')
        run(other, sys.executable, str(self.kit / 'tools/kit-adopt.py'), 'vendor', 'team-work.py', '--dest', 'scripts')
        git(other, 'add', '.'); git(other, 'commit', '-qm', 'custom install')
        probe = "import importlib.util; s=importlib.util.spec_from_file_location('team','scripts/team-work.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.kit_revision())"
        self.assertEqual(run(other, sys.executable, '-c', probe).strip(), self.revision)
        with (other / 'scripts/team-work.py').open('a') as f: f.write('\n# local change\n')
        self.assertIn('inconsistent provenance', run(other, sys.executable, 'scripts/team-work.py', 'claim',
            '--task','bad','--engineer','alice','--path','src','--criteria','Fixture passes',code=2))

    def test_unmanaged_dependency_collision_preserves_every_file(self):
        project = self.root / 'collision'; (project / 'tools').mkdir(parents=True)
        original = project / 'tools/project-check.py'; original.write_text('custom project checker\n')
        out = run(project, sys.executable, str(self.kit / 'tools/kit-adopt.py'), 'vendor', 'ledger.py', code=2)
        self.assertIn('not a managed regular file', out)
        self.assertEqual(original.read_text(), 'custom project checker\n')
        self.assertEqual(list((project / 'tools').iterdir()), [original])


if __name__ == '__main__':
    unittest.main()
