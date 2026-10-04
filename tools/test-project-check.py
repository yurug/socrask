#!/usr/bin/env python3
"""Exercise the ledger's failure boundaries; fixtures are not product acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOL = Path(__file__).with_name('project-check.py')
REVISION = 'a' * 40
ARTIFACT = 'sha256:' + 'b' * 64


def entity(id, status='active'):
    return dict(id=id, status=status, owner='named-owner', next_action='Review the observed result',
                review_on='2026-10-05', refs=['feedback.md'])


def fixture():
    project = dict(entity('P'), wip_limit=1)
    plan = dict(entity('PL'), project='P')
    task = dict(entity('T'), plan='PL', kind='product', depends_on=[], cases=['select'])
    feedback = dict(entity('S32', 'open'), task='T', events=[])
    return dict(version=1, sources=[dict(path='feedback.md', id_pattern=r'^\| (S\d+) \|')],
                projects=[project], plans=[plan], tasks=[task], feedback=[feedback])


def closed_fixture():
    data = fixture()
    task, feedback = data['tasks'][0], data['feedback'][0]
    task['status'] = 'closed'
    task['closure'] = {
        'implementation': dict(revision=REVISION, at='2026-10-02T10:00:00Z', ref='evidence.json'),
        'deployment': dict(revision=REVISION, artifact=ARTIFACT,
                           at='2026-10-02T11:00:00Z', ref='evidence.json'),
        'acceptance': dict(revision=REVISION, artifact=ARTIFACT, at='2026-10-02T12:00:00Z',
                           environment='representative-browser', ref='evidence.json',
                           cases=[dict(id='select', status='passed', ref='evidence.json')])}
    feedback.update(status='accepted', events=[dict(at='2026-10-02T12:00:00Z',
                                                   result='accepted', ref='evidence.json')])
    return data


class ProjectCheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'feedback.md').write_text('| ID | Request |\n| S32 | Drag a rectangle |\n')
        (self.root / 'evidence.json').write_text('{"note":"fixture, not product proof"}')

    def run_gate(self, data, code=0, reason=None, raw=None, as_of='2026-10-04'):
        path = self.root / 'ledger.json'
        path.write_text(raw if raw is not None else json.dumps(data))
        run = subprocess.run([sys.executable, str(TOOL), '--ledger', str(path),
                              '--root', str(self.root), '--as-of', as_of, '--summary'],
                             text=True, capture_output=True)
        self.assertEqual(run.returncode, code, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['coherent'], code == 0)
        if reason:
            self.assertIn(reason, '\n'.join(result['failures']))
        return result

    def test_PM_inventory_omission_cannot_hide_a_user_request(self):
        data = fixture()
        data['feedback'] = []
        self.run_gate(data, 2, 'untracked source IDs: S32')

    def test_PM_repeated_failure_reopens_same_task(self):
        data = closed_fixture()
        data['feedback'][0]['events'].append(dict(at='2026-10-03T12:00:00Z', result='failed', ref='feedback.md'))
        self.run_gate(data, 2, 'failure after acceptance')
        data['feedback'][0]['status'] = 'open'
        data['tasks'][0]['status'] = 'reopened'
        self.run_gate(data)

    def test_PM_coherent_is_not_product_acceptance(self):
        result = self.run_gate(fixture())
        self.assertFalse(result['product_acceptance_claimed'])
        self.assertEqual(result['counts']['active_tasks'], 1)

    def test_PM_imported_gaps_stay_visible_without_fabricated_cases(self):
        data = fixture()
        for group in ('tasks', 'feedback'):
            data[group][0].update(status='imported-unverified', migration_note='Historical claims need rechecking')
        data['tasks'][0]['cases'] = []
        result = self.run_gate(data)
        self.assertEqual(set(result['migration_gaps']), {'T', 'S32'})
        del data['tasks'][0]['migration_note']
        self.run_gate(data, 2, 'migration_note')

    def test_PM_owner_action_and_review_are_required(self):
        for field in ('owner', 'next_action', 'review_on'):
            with self.subTest(field=field):
                data = fixture()
                del data['tasks'][0][field]
                self.run_gate(data, 2, field)

    def test_PM_review_expires_for_pending_work_only(self):
        data = fixture()
        data['tasks'][0]['review_on'] = '2026-10-03'
        self.run_gate(data, 2, 'stale review_on')
        data = closed_fixture()
        data['tasks'][0]['review_on'] = data['feedback'][0]['review_on'] = '2026-01-01'
        self.run_gate(data)

    def test_PM_refs_exist_and_cannot_escape_root(self):
        for ref, reason in [('missing.md', 'missing reference'), ('../outside', 'outside root'),
                            ('https://example.com', 'relative local reference')]:
            data = fixture()
            data['tasks'][0]['refs'] = [ref]
            self.run_gate(data, 2, reason)
        (self.root / 'outside-link').symlink_to('/etc/passwd')
        data['tasks'][0]['refs'] = ['outside-link']
        self.run_gate(data, 2, 'outside root')

    def test_PM_unknown_duplicate_and_orphan_ids(self):
        for change, reason in [
            (lambda d: d['plans'][0].update(project='unknown'), 'unknown project'),
            (lambda d: d['tasks'][0].update(plan='unknown'), 'unknown plan'),
            (lambda d: d['feedback'][0].update(task='unknown'), 'unknown task'),
            (lambda d: d['tasks'].append(copy.deepcopy(d['tasks'][0])), 'duplicate ID'),
            (lambda d: d['tasks'][0].update(depends_on=['unknown']), 'unknown dependency'),
            (lambda d: d['feedback'][0].update(id='invented'), 'untracked source IDs')]:
            data = fixture()
            change(data)
            self.run_gate(data, 2, reason)

    def test_PM_dependency_cycle_and_unmet_dependency(self):
        data = fixture()
        second = dict(entity('T2', 'planned'), plan='PL', kind='product', depends_on=[], cases=['select'])
        data['tasks'].append(second)
        data['tasks'][0]['depends_on'] = ['T2']
        self.run_gate(data, 2, 'unmet dependency')
        data['tasks'][0]['status'] = 'planned'
        second['depends_on'] = ['T']
        self.run_gate(data, 2, 'dependency cycle')

    def test_PM_project_WIP_is_explicit_and_enforced(self):
        data = fixture()
        del data['projects'][0]['wip_limit']
        self.run_gate(data, 2, 'wip_limit')
        data = fixture()
        data['tasks'].append(dict(entity('T2', 'reopened'), plan='PL', kind='engineering', depends_on=[], cases=[]))
        self.run_gate(data, 2, 'WIP')

    def test_PM_product_closure_needs_exact_complete_evidence(self):
        self.run_gate(closed_fixture())
        mutations = [
            (lambda c: c.pop('implementation'), 'implementation'),
            (lambda c: c['deployment'].update(revision='c'*40), 'revision'),
            (lambda c: c['acceptance'].update(artifact='sha256:'+'c'*64), 'artifact'),
            (lambda c: c['acceptance'].update(cases=[]), 'case outcomes'),
            (lambda c: c['acceptance']['cases'][0].update(status='skipped'), 'passed'),
            (lambda c: c['acceptance'].update(at='2026-10-01T12:00:00Z'), 'chronology')]
        for mutate, reason in mutations:
            data = closed_fixture()
            mutate(data['tasks'][0]['closure'])
            self.run_gate(data, 2, reason)

    def test_PM_accepted_event_alone_cannot_close_feedback(self):
        data = fixture()
        data['feedback'][0].update(status='accepted', events=[dict(
            at='2026-10-02T12:00:00Z', result='accepted', ref='evidence.json')])
        self.run_gate(data, 2, 'closed task')

    def test_PM_reacceptance_needs_fresh_version_bound_recheck(self):
        data = closed_fixture()
        data['feedback'][0]['events'] += [
            dict(at='2026-10-03T10:00:00Z', result='failed', ref='feedback.md'),
            dict(at='2026-10-03T12:00:00Z', result='accepted', ref='evidence.json')]
        self.run_gate(data, 2, 'recheck after latest failure')
        data['tasks'][0]['closure']['acceptance']['at'] = '2026-10-03T12:00:00Z'
        self.run_gate(data)

    def test_PM_source_claims_are_not_observation_evidence(self):
        data = closed_fixture()
        data['tasks'][0]['closure']['acceptance']['ref'] = 'feedback.md'
        self.run_gate(data, 2, 'source inventory is not observed evidence')

    def test_PM_deferred_work_is_reviewed_without_consuming_WIP(self):
        data = fixture()
        data['tasks'][0]['status'] = data['feedback'][0]['status'] = 'deferred'
        data['projects'][0]['wip_limit'] = 0
        result = self.run_gate(data)
        self.assertEqual(result['counts']['active_tasks'], 0)
        self.run_gate(data, 2, 'stale review_on', as_of='2026-10-06')

    def test_PM_nonproduct_work_has_completion_evidence(self):
        data = fixture()
        task = dict(entity('T2', 'closed'), plan='PL', kind='engineering', depends_on=[], cases=[])
        data['tasks'].append(task)
        self.run_gate(data, 2, 'closure evidence')
        task['closure'] = dict(at='2026-10-03T12:00:00Z', ref='evidence.json')
        self.run_gate(data)

    def test_PM_nonproduct_feedback_acceptance_uses_its_observed_completion(self):
        for kind in ('engineering', 'process'):
            data = fixture()
            task, feedback = data['tasks'][0], data['feedback'][0]
            task.update(kind=kind, status='closed', cases=[],
                        closure=dict(at='2026-10-03T12:00:00Z', ref='evidence.json'))
            feedback.update(status='accepted', events=[
                dict(at='2026-10-03T10:00:00Z', result='failed', ref='feedback.md'),
                dict(at='2026-10-03T12:00:00Z', result='accepted', ref='evidence.json')])
            self.run_gate(data)
            task['closure']['at'] = '2026-10-02T12:00:00Z'
            self.run_gate(data, 2, 'recheck after latest failure')

    def test_PM_any_failed_report_requires_open_owned_followup(self):
        data = fixture()
        feedback, task = data['feedback'][0], data['tasks'][0]
        feedback['events'] = [dict(at='2026-10-03T10:00:00Z', result='failed', ref='feedback.md')]
        for state in ('planned', 'active', 'imported-unverified'):
            task.update(status=state, migration_note='Retained legacy claim')
            self.run_gate(data, 2, 'latest failure')
        task['status'] = 'blocked'
        self.assertEqual(self.run_gate(data)['counts']['active_tasks'], 0)
        feedback.update(status='imported-unverified', migration_note='Historical claim')
        self.run_gate(data, 2, 'latest failure')
        # Adding an accepted event without accepted task evidence must not hide it.
        feedback['events'].append(dict(at='2026-10-03T12:00:00Z', result='accepted', ref='evidence.json'))
        self.run_gate(data, 2, 'latest failure')
        feedback['status'] = 'open'
        task['status'] = 'reopened'
        self.run_gate(data)

    def test_PM_parent_closure_cannot_hide_pending_children(self):
        data = fixture()
        data['projects'][0]['status'] = 'closed'
        self.run_gate(data, 2, 'nonclosed plan')
        data = fixture()
        data['plans'][0]['status'] = 'closed'
        self.run_gate(data, 2, 'nonclosed task')

    def test_PM_rejection_requires_explicit_decision(self):
        data = fixture()
        data['feedback'][0]['status'] = 'waived'
        self.run_gate(data, 2, 'disposition')
        data['feedback'][0]['disposition'] = dict(rationale='Explicit scope decision', ref='feedback.md')
        self.run_gate(data)

    def test_PM_sources_have_real_unique_captured_IDs(self):
        for pattern, reason in [('bad(', 'regex'), ('S\\d+', 'one capture'),
                                ('(NO-MATCH)', 'no IDs'), ('(S)(\\d+)', 'one capture')]:
            data = fixture()
            data['sources'][0]['id_pattern'] = pattern
            self.run_gate(data, 2, reason)
        (self.root / 'feedback.md').write_text('| S32 | one |\n| S32 | two |\n')
        self.run_gate(fixture(), 2, 'duplicate source ID')

    def test_PM_malformed_inputs_have_JSON_diagnostics_without_traceback(self):
        malformed = ['[]', '{"version":1,"version":1}', '{"version":NaN}', '{']
        for raw in malformed:
            self.run_gate(None, 2, raw=raw)
        mutations = [lambda d: d.update(version=True), lambda d: d.update(tasks=None),
                     lambda d: d['tasks'][0].update(status=[]), lambda d: d['tasks'][0].update(cases=[{}]),
                     lambda d: d['feedback'][0].update(events=[None]),
                     lambda d: d['projects'][0].update(wip_limit=True),
                     lambda d: d['tasks'][0].update(review_on='2026-1-1'),
                     lambda d: d['feedback'][0].update(events=[dict(at='2026-10-02', result='failed', ref='feedback.md')])]
        for mutate in mutations:
            data = fixture()
            mutate(data)
            self.run_gate(data, 2)

    def test_PM_adversarial_nested_types_do_not_escape_JSON_diagnostics(self):
        # Ledger input is trusted, but accidental malformed edits must fail closed.
        for key, values in [('implementation', [None, [], 17]), ('deployment', [None, [], True]),
                            ('acceptance', [None, [], 'done'])]:
            for value in values:
                data = closed_fixture()
                data['tasks'][0]['closure'][key] = value
                self.run_gate(data, 2)
        for field in ('id', 'status', 'ref'):
            for value in (None, [], {}, True):
                data = closed_fixture()
                data['tasks'][0]['closure']['acceptance']['cases'][0][field] = value
                self.run_gate(data, 2)


if __name__ == '__main__':
    unittest.main()
