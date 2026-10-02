#!/usr/bin/env python3
"""Counterexamples to false acceptance: exercise the CLI, not its implementation."""
import copy
import datetime as dt
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).with_name('outcome-check.py')


class OutcomeGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.contract = {'version': 1, 'suite': 'core', 'revision': 'reviewed-v1', 'cases': [
            {'id': 'organize', 'fixture': 'large-tree-v1', 'checker': 'identity-v1',
             'feedback': ['F-12'], 'min_trials': 2, 'min_first_pass': 1, 'min_final_pass': 1},
            {'id': 'download', 'fixture': 'project-v1', 'checker': 'bytes-v1',
             'feedback': ['F-18'], 'min_trials': 2, 'min_first_pass': 1, 'min_final_pass': 1}]}
        now = dt.datetime.now(dt.timezone.utc)
        self.report = {'version': 1, 'suite': 'core', 'contract_revision': 'reviewed-v1',
            'complete': True, 'subject': {'revision': 'commit-A', 'artifact': 'sha256:A',
                'environment': 'test-linux', 'configuration': 'models-prompts-tools-v1'},
            'observed_before': 'sha256:A', 'observed_after': 'sha256:A',
            'started_at': (now-dt.timedelta(minutes=1)).isoformat(),
            'finished_at': now.isoformat(), 'trials': []}
        for case in self.contract['cases']:
            for n in range(2):
                self.report['trials'].append({'case': case['id'], 'id': str(n),
                    'fixture': case['fixture'], 'checker': case['checker'], 'attempts': [
                        {'status': 'passed', 'evidence': ['fixture://observed-state'],
                         'duration_ms': 100, 'cost': 0.01}]})

    def run_gate(self, baseline=None, extra=()):
        digest = hashlib.sha256(json.dumps(self.contract).encode()).hexdigest()
        for report in [self.report, baseline]:
            if report is not None:
                report.setdefault('contract_sha256', digest)
        for name, value in [('contract', self.contract), ('report', self.report), ('baseline', baseline)]:
            (self.root / (name+'.json')).write_text(json.dumps(value))
        cmd = [sys.executable, str(TOOL), '--contract', str(self.root/'contract.json'),
               '--report', str(self.root/'report.json'), '--revision', 'commit-A', '--artifact', 'sha256:A']
        if baseline is not None:
            cmd += ['--baseline', str(self.root/'baseline.json')]
        result = subprocess.run(cmd + list(extra), capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def assert_blocked(self, baseline=None):
        code, out = self.run_gate(baseline)
        self.assertNotEqual(code, 0)
        self.assertFalse(out['accepted'])

    def test_complete_observed_results_pass(self):
        code, out = self.run_gate()
        self.assertEqual(code, 0)
        self.assertTrue(out['accepted'])
        self.assertEqual(out['cases']['organize']['first_pass_rate'], 1)
        self.assertEqual(out['cases']['organize']['feedback'], ['F-12'])

    def test_missing_case_is_not_zero_regressions(self):
        self.report['trials'] = self.report['trials'][:2]
        self.assert_blocked()

    def test_skipped_and_unknown_are_incomplete(self):
        for status in ['skipped', 'unknown']:
            with self.subTest(status=status):
                self.report['trials'][0]['attempts'][0]['status'] = status
                self.assert_blocked()

    def test_retry_does_not_erase_first_failure(self):
        attempts = self.report['trials'][0]['attempts']
        attempts.insert(0, dict(attempts[0], status='failed'))
        code, out = self.run_gate()
        self.assertNotEqual(code, 0)
        self.assertEqual(out['cases']['organize']['first_pass_rate'], .5)
        self.assertEqual(out['cases']['organize']['final_pass_rate'], 1)
        self.assertEqual(out['cases']['organize']['recovered_trials'], 1)
        self.assertAlmostEqual(out['cases']['organize']['cost'], .03)

    def test_predeclared_recovery_policy_can_pass(self):
        self.contract['cases'][0]['min_first_pass'] = .5
        a = self.report['trials'][0]['attempts']
        a.insert(0, dict(a[0], status='failed'))
        self.assertEqual(self.run_gate()[0], 0)

    def test_first_pass_drop_blocks_even_above_minimum(self):
        baseline = copy.deepcopy(self.report)
        self.contract['cases'][0]['min_first_pass'] = .5
        a = self.report['trials'][0]['attempts']
        a.insert(0, dict(a[0], status='failed'))
        code, out = self.run_gate(baseline)
        self.assertNotEqual(code, 0)
        self.assertIn('organize', out['regressions'])

    def test_deleted_contract_case_cannot_erase_baseline(self):
        baseline = copy.deepcopy(self.report)
        self.contract['cases'].pop()
        self.report['trials'] = self.report['trials'][:2]
        self.assert_blocked(baseline)

    def test_incompatible_checker_is_not_a_comparison(self):
        baseline = copy.deepcopy(self.report)
        baseline['trials'][0]['checker'] = 'old-checker'
        self.assert_blocked(baseline)

    def test_actual_improvement_is_reported(self):
        baseline = copy.deepcopy(self.report)
        baseline['trials'][0]['attempts'][0]['status'] = 'failed'
        code, out = self.run_gate(baseline)
        self.assertEqual(code, 0)
        self.assertIn('organize', out['improvements'])

    def test_release_identity_and_start_end_observations(self):
        for field in ['revision', 'artifact', 'environment', 'configuration']:
            with self.subTest(field=field):
                old = self.report['subject'][field]
                self.report['subject'][field] = 'other' if field in ['revision','artifact'] else ''
                self.assert_blocked()
                self.report['subject'][field] = old
        self.report['observed_after'] = 'sha256:B'
        self.assert_blocked()

    def test_insufficient_repetitions_and_duplicate_trials(self):
        self.report['trials'].pop()
        self.assert_blocked()
        self.report['trials'].append(copy.deepcopy(self.report['trials'][0]))
        self.assert_blocked()

    def test_missing_outcome_evidence_fails(self):
        self.report['trials'][0]['attempts'][0]['evidence'] = []
        self.assert_blocked()

    def test_crash_and_stale_reports_fail(self):
        self.report['complete'] = False
        self.assert_blocked()
        self.report['complete'] = True
        self.report['started_at'] = '2020-01-01T00:00:00+00:00'
        self.report['finished_at'] = '2020-01-01T00:01:00+00:00'
        self.assert_blocked()

    def test_future_naive_and_reversed_times_fail(self):
        for value in ['2099-01-01T00:00:00+00:00', '2026-01-01T00:00:00', 'invalid']:
            with self.subTest(value=value):
                self.report['finished_at'] = value
                self.assert_blocked()

    def test_nonfinite_and_boolean_numbers_rejected(self):
        for value in [float('nan'), float('inf'), True, -1]:
            with self.subTest(value=value):
                self.report['trials'][0]['attempts'][0]['cost'] = value
                self.assert_blocked()

    def test_inputs_never_mutated(self):
        self.run_gate()
        before = (self.root/'report.json').read_bytes()
        self.run_gate()
        self.assertEqual((self.root/'report.json').read_bytes(), before)

    def test_contract_change_invalidates_old_evidence(self):
        self.assertEqual(self.run_gate()[0], 0)
        self.contract['cases'][0]['min_first_pass'] = .2
        self.assert_blocked()

    def test_no_trial_can_continue_after_success(self):
        a = self.report['trials'][0]['attempts']
        a.append(copy.deepcopy(a[0]))
        self.assert_blocked()

    def test_zero_success_cannot_be_an_accepted_required_case(self):
        self.contract['cases'][0].update(min_first_pass=0, min_final_pass=0)
        self.assert_blocked()

    def test_duplicate_json_keys_and_truncated_input_are_rejected(self):
        bad = self.root/'bad.json'
        for text in ['{"version":1,"version":1}', '{"version":']:
            with self.subTest(text=text):
                bad.write_text(text)
                code, out = self.run_gate(extra=['--report',str(bad)])
                self.assertEqual(code, 2)
                self.assertFalse(out['accepted'])


if __name__ == '__main__':
    unittest.main()
