#!/usr/bin/env python3
"""Read-only acceptance of observed user outcomes; contract: docs/outcome-quality.md.

The caller owns execution and promotion. This tool rejects incomplete evidence,
keeps first attempts visible, and never silently rewrites the comparison baseline.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(value):
    return isinstance(value, str) and bool(value.strip())


def number(value, minimum=0, maximum=math.inf):
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def read(path):
    raw = Path(path).read_bytes()
    value = json.loads(raw, object_pairs_hook=object_pairs)
    require(isinstance(value, dict) and type(value.get('version')) is int
            and value['version'] == 1, 'expected version-1 JSON object')
    return value, hashlib.sha256(raw).hexdigest()


def timestamp(value):
    require(string(value), 'timestamps must be nonempty strings')
    time = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(time.tzinfo is not None, 'timestamps need a timezone')
    return time


def contract_cases(contract):
    require(string(contract.get('suite')) and string(contract.get('revision')), 'contract needs suite/revision')
    rows = contract.get('cases')
    require(isinstance(rows, list) and rows, 'contract needs nonempty cases')
    cases = {}
    for row in rows:
        require(isinstance(row, dict), 'case must be an object')
        require(all(string(row.get(k)) for k in ('id', 'fixture', 'checker')), 'case needs id/fixture/checker')
        require(row['id'] not in cases, f"duplicate case: {row['id']}")
        require(type(row.get('min_trials')) is int and row['min_trials'] > 0, 'min_trials must be positive integer')
        require(number(row.get('min_first_pass'), 0, 1) and number(row.get('min_final_pass'), 0, 1), 'invalid rate thresholds')
        require(row['min_final_pass'] > 0, 'required cases need a positive final success threshold')
        require(row['min_final_pass'] >= row['min_first_pass'], 'final threshold cannot be below first-attempt threshold')
        feedback = row.get('feedback')
        require(isinstance(feedback, list) and feedback and all(string(x) for x in feedback), 'case needs feedback IDs')
        require(len(set(feedback)) == len(feedback), 'duplicate feedback ID')
        cases[row['id']] = row
    return cases


def validate_header(report, contract, contract_hash, now):
    require(report.get('complete') is True, 'report is incomplete')
    require(report.get('suite') == contract['suite'] and report.get('contract_revision') == contract['revision'],
            'incompatible suite/contract revision')
    require(report.get('contract_sha256') == contract_hash, 'report does not bind the exact reviewed contract')
    subject = report.get('subject')
    require(isinstance(subject, dict) and all(string(subject.get(k)) for k in
            ('revision', 'artifact', 'environment', 'configuration')), 'subject needs revision/artifact/environment/configuration')
    require(report.get('observed_before') == subject['artifact'] == report.get('observed_after'),
            'artifact not observed unchanged at both boundaries')
    start, end = timestamp(report.get('started_at')), timestamp(report.get('finished_at'))
    require(start <= end <= now, 'reversed or future report timestamps')
    return end


def validate_attempts(attempts):
    require(isinstance(attempts, list) and attempts, 'trial needs chronological attempts')
    for a in attempts:
        require(isinstance(a, dict), 'attempt must be an object')
        require(a.get('status') in ('passed', 'failed', 'skipped', 'unknown'), 'invalid attempt status')
        require(a['status'] not in ('skipped', 'unknown'), 'skipped/unknown attempt is incomplete evidence')
        refs = a.get('evidence')
        require(isinstance(refs, list) and refs and all(string(x) for x in refs), 'attempt needs outcome evidence')
        require(number(a.get('duration_ms')) and number(a.get('cost')), 'invalid or missing duration/cost')
    # A success ends a trial. Further independent samples must retain separate IDs.
    require(all(a['status'] != 'passed' for a in attempts[:-1]), 'attempts after success need a new trial ID')


def group_trials(report, cases):
    trials = report.get('trials')
    require(isinstance(trials, list) and trials, 'report needs trials')
    groups = {case: [] for case in cases}
    seen = set()
    for row in trials:
        require(isinstance(row, dict) and string(row.get('case')) and string(row.get('id')), 'trial needs case/id')
        case = row['case']
        require(case in cases, f'undeclared case: {case}')
        key = (case, row['id'])
        require(key not in seen, f'duplicate trial: {key}')
        seen.add(key)
        require(all(row.get(k) == cases[case][k] for k in ('fixture', 'checker')), f'incompatible fixture/checker: {case}')
        validate_attempts(row.get('attempts'))
        groups[case].append(row['attempts'])
    for case, rows in groups.items():
        require(len(rows) >= cases[case]['min_trials'], f'missing/insufficient trials: {case}')
    return groups


def summarize(groups, cases):
    output = {}
    for case, trials in groups.items():
        first = sum(a[0]['status'] == 'passed' for a in trials)
        final = sum(a[-1]['status'] == 'passed' for a in trials)
        cost = sum(a['cost'] for trial in trials for a in trial)
        duration = sum(a['duration_ms'] for trial in trials for a in trial)
        require(number(cost) and number(duration), 'aggregate cost/duration overflow')
        output[case] = {'trials': len(trials), 'first_pass_rate': first/len(trials),
            'final_pass_rate': final/len(trials), 'recovered_trials': final-first,
            'duration_ms': duration, 'cost': cost, 'cost_per_success': cost/final if final else None,
            'feedback': cases[case]['feedback']}
    return output


def evaluate(args):
    contract, contract_hash = read(args.contract)
    cases = contract_cases(contract)
    report, report_hash = read(args.report)
    now = dt.datetime.now(dt.timezone.utc)
    end = validate_header(report, contract, contract_hash, now)
    require(number(args.max_age_hours) and args.max_age_hours > 0, 'age limit must be positive and finite')
    require((now-end).total_seconds() <= args.max_age_hours*3600, 'current report is stale')
    require(report['subject']['revision'] == args.revision, 'unexpected source revision')
    require(report['subject']['artifact'] == args.artifact, 'unexpected artifact')
    current = summarize(group_trials(report, cases), cases)
    previous, baseline_hash = {}, None
    if args.baseline:
        baseline, baseline_hash = read(args.baseline)
        validate_header(baseline, contract, contract_hash, now)
        require(baseline['subject']['environment'] == report['subject']['environment'], 'incompatible baseline environment')
        require(timestamp(baseline['finished_at']) <= end, 'baseline is newer than current report')
        previous = summarize(group_trials(baseline, cases), cases)
    reasons, regressions, improvements = [], [], []
    for case, result in current.items():
        for rate, threshold in [('first_pass_rate', 'min_first_pass'), ('final_pass_rate', 'min_final_pass')]:
            if result[rate] < cases[case][threshold]:
                reasons.append(f'{case}: {rate} below declared minimum')
        if case in previous:
            rates = ['first_pass_rate', 'final_pass_rate']
            if any(result[k] < previous[case][k] for k in rates):
                regressions.append(case)
            elif any(result[k] > previous[case][k] for k in rates):
                improvements.append(case)
    reasons += [f'{case}: measured success-rate regression' for case in regressions]
    return {'accepted': not reasons, 'reasons': reasons, 'cases': current,
        'regressions': regressions, 'improvements': improvements,
        'initial_baseline': not bool(args.baseline), 'subject': report['subject'],
        'contract_sha256': contract_hash, 'report_sha256': report_hash, 'baseline_sha256': baseline_hash}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('contract', 'report', 'revision', 'artifact'):
        parser.add_argument('--'+field, required=True)
    parser.add_argument('--baseline')
    parser.add_argument('--max-age-hours', type=float, default=24)
    args = parser.parse_args()
    try:
        result = evaluate(args)
        code = 0 if result['accepted'] else 1
    except (ValueError, OSError, UnicodeError, OverflowError) as error:
        result, code = {'accepted': False, 'reasons': [str(error)], 'evidence_status': 'invalid-or-incomplete'}, 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
