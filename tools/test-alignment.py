#!/usr/bin/env python3
"""Deterministic checkpoint consistency fixtures."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('alignment', Path(__file__).with_name('alignment-check.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.record = {'version': 1, 'work_id': 'task', 'tier': 'slice', 'base': 'a'*40,
                       'checkpoints': {'inbrief': {'status': 'not-required', 'reason': 'Familiar API; no new decision'},
                                       'backbrief': {'status': 'required', 'reason': 'Aggregate API diff'}}}

    def test_start_and_pending_finish(self):
        self.assertEqual([], module.validate(self.record, 'start'))
        self.assertTrue(module.validate(self.record, 'finish'))

    def test_human_complete_requires_evidence(self):
        self.record['head'] = 'b'*40
        entry = self.record['checkpoints']['backbrief']
        entry['status'] = 'human-complete'
        self.assertTrue(module.validate(self.record, 'finish'))
        entry['evidence'] = {'kind': 'human-event', 'ref': 'backbrief:session1:event12'}
        self.assertEqual([], module.validate(self.record, 'finish', 'a'*40, 'b'*40))
        self.assertTrue(module.validate(self.record, 'finish', 'a'*40, 'c'*40))

    def test_degraded_needs_authorization(self):
        self.record['head'] = 'b'*40
        entry = self.record['checkpoints']['backbrief']
        entry.update(status='degraded-authorized', evidence={'kind': 'human-event', 'ref': 'URL sent'})
        self.assertTrue(module.validate(self.record, 'finish'))
        entry['evidence'] = {'kind': 'human-authorization', 'ref': 'conversation:turn7'}
        self.assertEqual([], module.validate(self.record, 'finish'))

    def test_non_direct_cannot_skip_backbrief(self):
        self.record['head'] = 'b'*40
        self.record['checkpoints']['backbrief']['status'] = 'not-required'
        self.assertTrue(module.validate(self.record, 'finish'))
        self.record['tier'] = 'direct'
        self.assertEqual([], module.validate(self.record, 'finish'))

    def test_full_requires_inbrief(self):
        self.record['tier'] = 'full'
        self.assertTrue(module.validate(self.record, 'start'))
        self.record['checkpoints']['inbrief']['status'] = 'pending'
        self.assertTrue(module.validate(self.record, 'start'))

    def test_malformed_records_fail(self):
        for record in (None, [], {}, {'version': True}, dict(self.record, checkpoints=[])):
            with self.subTest(record=record):
                self.assertTrue(module.validate(record, 'start'))
        for key in ('work_id', 'base', 'tier'):
            record = copy.deepcopy(self.record)
            record[key] = None
            self.assertTrue(module.validate(record, 'start'))


if __name__ == '__main__':
    unittest.main()
