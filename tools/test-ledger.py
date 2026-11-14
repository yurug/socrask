#!/usr/bin/env python3
"""Read, write and archive cases for ledger.py, on project-check.py's fixtures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).with_name('ledger.py')
spec = importlib.util.spec_from_file_location('fixtures', Path(__file__).with_name('test-project-check.py'))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


class LedgerTool(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'feedback.md').write_text('| ID | Request |\n| S32 | Drag a rectangle |\n')
        (self.root / 'evidence.json').write_text('{"note":"fixture"}')
        self.path = self.root / 'kb/work/ledger.json'
        self.path.parent.mkdir(parents=True)
        self.archive = self.root / 'kb/work/ledger-archive.json'

    def save(self, data, indent=1):
        self.path.write_text(json.dumps(data, indent=indent) + '\n')

    def run_tool(self, *args, code=0):
        run = subprocess.run([sys.executable, str(TOOL), '--as-of', '2026-10-04', *args],
                             cwd=self.root, text=True, capture_output=True, timeout=10)
        self.assertEqual(run.returncode, code, run.stdout + run.stderr)
        return run.stdout

    def test_get_prints_one_line(self):
        self.save(fixtures.fixture())
        out = self.run_tool('get', 'T')
        self.assertEqual(out.count('\n'), 1)
        self.assertEqual(json.loads(out)['plan'], 'PL')
        self.assertIn('unknown ID: T9', self.run_tool('get', 'T9', code=1))

    def test_list_filters_and_stays_short(self):
        self.save(fixtures.fixture())
        out = self.run_tool('list', 'tasks', '--status', 'active')
        self.assertEqual(out, 'T\tactive\tnamed-owner\t2026-10-05\tReview the observed result\nledger: 1 entries\n')
        self.assertIn('ledger: 0 entries', self.run_tool('list', '--owner', 'nobody'))
        self.assertIn('ledger: 0 entries', self.run_tool('list', '--due', '2026-10-01'))

    def test_set_changes_fields_and_keeps_the_format(self):
        self.save(fixtures.fixture(), indent=1)
        out = self.run_tool('set', 'T', 'status=blocked', 'next_action=Wait for the owner', 'cases=["select","grid"]')
        self.assertEqual(out, 'ledger: set T status, next_action, cases\n')
        data = json.loads(self.path.read_text())
        self.assertEqual((data['tasks'][0]['status'], data['tasks'][0]['cases']), ('blocked', ['select', 'grid']))
        self.assertTrue(self.path.read_text().startswith('{\n "version"'))

    def test_write_that_breaks_a_coherent_ledger_is_refused(self):
        self.save(fixtures.fixture())
        before = self.path.read_text()
        out = self.run_tool('set', 'T', 'status=closed', code=1)
        self.assertIn('refused: the ledger would become incoherent: T: closure evidence required', out)
        self.assertEqual(self.path.read_text(), before)

    def test_incoherent_ledger_accepts_fixes_one_at_a_time(self):
        data = fixtures.fixture()
        data['tasks'][0]['review_on'] = data['plans'][0]['review_on'] = '2026-10-01'
        self.save(data)
        out = self.run_tool('set', 'PL', 'review_on=2026-10-10')
        self.assertIn('still incoherent: T: stale review_on', out)
        self.assertNotIn('still incoherent', self.run_tool('set', 'T', 'review_on=2026-10-10'))

    def test_dotted_field_and_file_value(self):
        self.save(fixtures.fixture())
        (self.root / 'closure.json').write_text('{"ref": "evidence.json"}')
        self.run_tool('set', 'P', 'notes.origin=@closure.json', 'notes.kind=import')
        self.assertEqual(json.loads(self.path.read_text())['projects'][0]['notes'],
                         {'origin': {'ref': 'evidence.json'}, 'kind': 'import'})
        self.assertIn('the id is', self.run_tool('set', 'P', 'id=Q', code=1))

    def test_add_and_event(self):
        self.save(fixtures.fixture())
        task = dict(fixtures.entity('T2', 'planned'), plan='PL', kind='engineering', depends_on=['T'], cases=[])
        self.assertIn('added T2 to tasks', self.run_tool('add', 'tasks', json.dumps(task)))
        self.assertIn('duplicate ID: T2', self.run_tool('add', 'tasks', json.dumps(task), code=1))
        out = self.run_tool('event', 'S32', '--result', 'accepted', '--ref', 'evidence.json',
                            '--at', '2026-10-03T10:00:00Z')
        self.assertIn('S32: accepted event', out)
        self.assertIn('events belong to feedback', self.run_tool('event', 'T', '--result', 'failed',
                                                                 '--ref', 'feedback.md', code=1))

    def test_archive_moves_only_finished_entries_and_project_check_reads_both(self):
        data = fixtures.closed_fixture()
        data['plans'][0]['status'] = 'closed'
        data['plans'][0]['closure'] = {}
        live = dict(fixtures.entity('PL2'), project='P')
        data['plans'].append(live)
        self.save(data)
        self.assertIn('archived 3 entries', self.run_tool('archive'))
        kept = json.loads(self.path.read_text())
        self.assertEqual([r['id'] for g in ('projects', 'plans', 'tasks', 'feedback') for r in kept[g]], ['P', 'PL2'])
        archived = json.loads(self.archive.read_text())
        self.assertEqual([r['id'] for r in archived['tasks']], ['T'])
        self.assertEqual(json.loads(self.run_tool('get', 'S32'))['status'], 'accepted')
        self.assertIn('ledger: 0 entries', self.run_tool('list', 'tasks'))
        self.assertIn('ledger: 1 entries', self.run_tool('list', 'tasks', '--archived'))
        check = subprocess.run([sys.executable, str(TOOL.with_name('project-check.py')), '--ledger',
                                str(self.path), '--root', str(self.root), '--as-of', '2026-10-04'],
                               text=True, capture_output=True)
        self.assertEqual(check.returncode, 0, check.stdout)
        self.assertEqual(json.loads(check.stdout)['counts']['tasks'], 1)

    def test_backlog_by_priority_and_an_iteration(self):
        data = fixtures.fixture()
        for i, prio in ((2, 3), (3, 1)):
            data['tasks'].append(dict(fixtures.entity(f'T{i}', 'planned'), plan='PL', kind='engineering',
                                      depends_on=[], cases=[], priority=prio, value='v'))
        self.save(data)
        out = self.run_tool('list', 'tasks', '--by-priority')
        self.assertEqual([l.split('\t')[0] for l in out.splitlines()[:3]], ['T3', 'T2', 'T'])
        iteration = dict(fixtures.entity('I1', 'active'), project='P', goal='Backlog head', tasks=['T3'],
                         start='2026-10-01', end='2026-10-14')
        self.assertIn('added I1 to iterations', self.run_tool('add', 'iterations', json.dumps(iteration)))
        bad = dict(iteration, id='I2', tasks=['T'])
        out = self.run_tool('add', 'iterations', json.dumps(bad), code=1)
        self.assertIn('T: an iteration task needs an integer priority', out)

    def test_unreadable_ledger(self):
        self.path.write_text('{"version": 1, "version": 1}')
        self.assertIn('duplicate JSON key', self.run_tool('list', code=2))


if __name__ == '__main__':
    unittest.main()
