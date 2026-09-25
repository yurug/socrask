#!/usr/bin/env python3
"""Check declared alignment state; this cannot authenticate human evidence."""
import argparse
import json
from pathlib import Path
import re
import sys


def validate(record, stage, base=None, head=None):
    """Return actionable errors, including stale diff bounds and unfinished gates."""
    errors = []
    if not isinstance(record, dict):
        return ['record must be an object']
    if type(record.get('version')) is not int or record['version'] != 1:
        errors.append('version must be 1')
    if not isinstance(record.get('work_id'), str) or not record['work_id'].strip():
        errors.append('work_id is required')
    tier = record.get('tier')
    if tier not in ('direct', 'slice', 'full'):
        errors.append('tier must be direct, slice, or full')
    for key, expected in (('base', base), ('head', head)):
        value = record.get(key)
        if key == 'head' and stage == 'start' and value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', value):
            errors.append(f'{key} must be a full commit hash')
        if expected is not None and value != expected:
            errors.append(f'{key} does not match the current work diff')
    checkpoints = record.get('checkpoints')
    if not isinstance(checkpoints, dict):
        return errors + ['checkpoints must be an object']
    for name in ('inbrief', 'backbrief'):
        entry = checkpoints.get(name)
        if not isinstance(entry, dict):
            errors.append(f'{name}: checkpoint is required')
            continue
        status = entry.get('status')
        if status not in ('required', 'pending', 'human-complete', 'degraded-authorized', 'not-required'):
            errors.append(f'{name}: unknown status')
            continue
        if not isinstance(entry.get('reason'), str) or not entry['reason'].strip():
            errors.append(f'{name}: reason is required')
        if status == 'not-required' and ((name == 'backbrief' and tier != 'direct') or (name == 'inbrief' and tier == 'full')):
            errors.append(f'{name}: cannot be not-required for {tier}')
        if status in ('required', 'pending') and (stage == 'finish' or name == 'inbrief'):
            errors.append(f'{name}: {status}; checkpoint is not settled')
        if status in ('human-complete', 'degraded-authorized'):
            evidence = entry.get('evidence')
            kind = 'human-event' if status == 'human-complete' else 'human-authorization'
            if not isinstance(evidence, dict) or evidence.get('kind') != kind or not isinstance(evidence.get('ref'), str) or not evidence['ref'].strip():
                errors.append(f'{name}: {kind} evidence reference is required')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    parser.add_argument('--stage', required=True, choices=('start', 'finish'))
    parser.add_argument('--base')
    parser.add_argument('--head')
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text())
        errors = validate(record, args.stage, args.base, args.head)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(f'alignment: {error}', file=sys.stderr)
    if errors:
        return 1
    print('alignment: declared checkpoints satisfy the gate (human evidence is not authenticated)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
