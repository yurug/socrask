#!/usr/bin/env python3
"""Check that declared commitments remain owned, schedulable and evidence-bound.

Contract: docs/project-management.md. Exit 0 means ledger coherence, never user
acceptance; exit 2 means invalid/incomplete control data. The ledger is trusted
input: this gate cannot discover undeclared sources or authenticate observations.
"""
import argparse
from collections import Counter, deque
import datetime as dt
import json
from pathlib import Path
import re
import sys


WORK_STATUSES = {'planned', 'active', 'blocked', 'deferred', 'imported-unverified', 'closed'}
FEEDBACK_STATUSES = {'open', 'deferred', 'imported-unverified', 'accepted', 'rejected', 'waived'}
TERMINAL = {'closed', 'accepted', 'rejected', 'waived'}
RUNNING = {'active', 'reopened'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, label, nonempty=False):
    require(isinstance(value, list) and all(string(item) for item in value), f'{label}: expected string array')
    require(not nonempty or value, f'{label}: must not be empty')
    require(len(set(value)) == len(value), f'{label}: duplicate values')
    return value


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def date(value):
    require(string(value) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'expected YYYY-MM-DD date')
    return dt.date.fromisoformat(value)


class Ledger:
    """Own validation context: one filesystem root, review date and source inventory."""

    def __init__(self, root, as_of):
        self.root, self.as_of = Path(root).resolve(), date(as_of)
        require(self.root.is_dir(), 'root must be a directory')
        self.sources, self.groups, self.gaps = {}, {}, []

    def ref(self, value, label, observation=False):
        """Resolve local references inside root; anchors remain a documented limit."""
        require(string(value), f'{label}: missing reference')
        path = value.split('#', 1)[0]
        require(path and not Path(path).is_absolute() and '://' not in path,
                f'{label}: expected relative local reference')
        target = (self.root / path).resolve()
        require(target.is_relative_to(self.root), f'{label}: reference outside root')
        require(target.is_file(), f'{label}: missing reference: {path}')
        if observation:
            require(target not in self.sources.values(), f'{label}: source inventory is not observed evidence')
        return target

    def time(self, value, label):
        require(string(value), f'{label}: timestamp required')
        time = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(time.tzinfo is not None, f'{label}: timestamp needs timezone')
        require(time.astimezone(dt.timezone.utc).date() <= self.as_of, f'{label}: future timestamp')
        return time

    def inventory(self, sources):
        require(isinstance(sources, list) and sources, 'sources: nonempty declared inventory required')
        for source in sources:
            require(isinstance(source, dict), 'source must be an object')
            path = self.ref(source.get('path'), 'source')
            require(string(source.get('id_pattern')), 'source needs id_pattern')
            try:
                pattern = re.compile(source['id_pattern'], re.MULTILINE)
            except re.error as error:
                raise ValueError(f'invalid source regex: {error}') from error
            require(pattern.groups == 1, 'source regex needs exactly one capture group')
            ids = pattern.findall(path.read_text())
            require(ids and all(string(id) for id in ids), f'source yielded no IDs: {source["path"]}')
            for id in ids:
                require(id not in self.sources, f'duplicate source ID: {id}')
                self.sources[id] = path

    def entities(self, group, rows):
        require(isinstance(rows, list), f'{group}: expected array')
        result = {}
        allowed = FEEDBACK_STATUSES if group == 'feedback' else WORK_STATUSES | ({'reopened'} if group == 'tasks' else set())
        for row in rows:
            require(isinstance(row, dict), f'{group}: expected objects')
            id = row.get('id')
            require(string(id), f'{group}: id required')
            require(id not in result and not any(id in g for g in self.groups.values()), f'duplicate ID: {id}')
            for key in ('owner', 'next_action', 'review_on'):
                require(string(row.get(key)), f'{id}: {key} required')
            require(string(row.get('status')) and row['status'] in allowed, f'{id}: invalid status')
            review = date(row['review_on'])
            require(row['status'] in TERMINAL or review >= self.as_of, f'{id}: stale review_on')
            for ref in strings(row.get('refs'), f'{id}.refs', nonempty=True):
                self.ref(ref, id)
            if row['status'] == 'imported-unverified':
                require(string(row.get('migration_note')), f'{id}: migration_note required')
                self.gaps.append(id)
            result[id] = row
        self.groups[group] = result

    def product_closure(self, task):
        """Check delivery facts are distinct, version-bound and cover every case."""
        id, closure = task['id'], task.get('closure')
        require(isinstance(closure, dict), f'{id}: closure evidence required')
        stages = [closure.get(name) for name in ('implementation', 'deployment', 'acceptance')]
        for name, stage in zip(('implementation', 'deployment', 'acceptance'), stages):
            require(isinstance(stage, dict), f'{id}: {name} evidence required')
            require(string(stage.get('revision')) and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', stage['revision']),
                    f'{id}: {name} needs full source revision')
            self.ref(stage.get('ref'), f'{id}.{name}', observation=True)
        implementation, deployment, acceptance = stages
        require(implementation['revision'] == deployment['revision'] == acceptance['revision'],
                f'{id}: closure revision mismatch')
        artifact = deployment.get('artifact')
        require(string(artifact) and re.fullmatch(r'sha256:[0-9a-f]{64}', artifact), f'{id}: immutable artifact required')
        require(acceptance.get('artifact') == artifact, f'{id}: acceptance artifact mismatch')
        times = [self.time(stage.get('at'), id) for stage in stages]
        require(times == sorted(times), f'{id}: closure chronology invalid')
        require(string(acceptance.get('environment')), f'{id}: acceptance environment required')
        cases = acceptance.get('cases')
        require(isinstance(cases, list) and cases, f'{id}: complete case outcomes required')
        seen = set()
        for case in cases:
            require(isinstance(case, dict) and string(case.get('id')), f'{id}: invalid case outcome')
            require(case['id'] not in seen, f'{id}: duplicate case outcome')
            seen.add(case['id'])
            require(case.get('status') == 'passed', f'{id}: every required case must have passed')
            self.ref(case.get('ref'), f'{id}.{case["id"]}', observation=True)
        require(seen == set(task['cases']), f'{id}: case outcomes differ from declared cases')
        return times[-1]

    def tasks(self):
        projects, plans, tasks = (self.groups[g] for g in ('projects', 'plans', 'tasks'))
        for project in projects.values():
            require(type(project.get('wip_limit')) is int and project['wip_limit'] >= 0,
                    f'{project["id"]}: explicit nonnegative integer wip_limit required')
        for plan in plans.values():
            require(string(plan.get('project')) and plan['project'] in projects, f'{plan["id"]}: unknown project')
        active = Counter()
        for id, task in tasks.items():
            require(string(task.get('plan')) and task['plan'] in plans, f'{id}: unknown plan')
            require(string(task.get('kind')) and task['kind'] in ('product', 'engineering', 'process'), f'{id}: invalid kind')
            strings(task.get('cases'), f'{id}.cases', task['kind'] == 'product' and task['status'] != 'imported-unverified')
            for dep in strings(task.get('depends_on'), f'{id}.depends_on'):
                require(dep in tasks, f'{id}: unknown dependency: {dep}')
                require(task['status'] not in RUNNING | {'closed'} or tasks[dep]['status'] == 'closed', f'{id}: unmet dependency: {dep}')
            if task['status'] in RUNNING:
                active[plans[task['plan']]['project']] += 1
            if task['status'] == 'closed':
                if task['kind'] == 'product':
                    self.product_closure(task)
                else:
                    closure = task.get('closure')
                    require(isinstance(closure, dict), f'{id}: closure evidence required')
                    self.ref(closure.get('ref'), id, observation=True)
                    self.time(closure.get('at'), id)
        for id, project in projects.items():
            require(active[id] <= project['wip_limit'], f'{id}: WIP {active[id]} exceeds {project["wip_limit"]}')
        return active

    def dependencies(self):
        """Kahn's traversal detects cycles without recursion limits on large imports."""
        tasks = self.groups['tasks']
        degree = {id: len(task['depends_on']) for id, task in tasks.items()}
        users = {id: [] for id in tasks}
        for id, task in tasks.items():
            for dep in task['depends_on']:
                users[dep].append(id)
        ready = deque(id for id in tasks if degree[id] == 0)
        visited = 0
        while ready:
            visited += 1
            for user in users[ready.popleft()]:
                degree[user] -= 1
                if degree[user] == 0:
                    ready.append(user)
        require(visited == len(tasks), 'dependency cycle in task graph')

    def feedback(self):
        feedback, tasks = self.groups['feedback'], self.groups['tasks']
        missing, extra = set(self.sources) - feedback.keys(), feedback.keys() - set(self.sources)
        require(not missing, 'untracked source IDs: ' + ', '.join(sorted(missing)))
        require(not extra, 'feedback IDs absent from source inventory: ' + ', '.join(sorted(extra)))
        for id, row in feedback.items():
            require(string(row.get('task')) and row['task'] in tasks, f'{id}: unknown task')
            require(self.sources[id] in [self.ref(ref, id) for ref in row['refs']], f'{id}: refs omit its source inventory')
            if row['status'] in ('waived', 'rejected'):
                decision = row.get('disposition')
                require(isinstance(decision, dict) and string(decision.get('rationale')), f'{id}: explicit disposition required')
                self.ref(decision.get('ref'), id)
            self.feedback_events(row, tasks[row['task']])

    def feedback_events(self, row, task):
        """A later complaint invalidates an earlier success on the same task ID."""
        id, events = row['id'], row.get('events')
        require(isinstance(events, list), f'{id}: events array required')
        history = []
        for event in events:
            require(isinstance(event, dict) and event.get('result') in ('failed', 'accepted'), f'{id}: invalid event')
            history.append((self.time(event.get('at'), id), event['result']))
            self.ref(event.get('ref'), id)
        require([t for t, _ in history] == sorted(t for t, _ in history), f'{id}: events must be chronological')
        failed = [t for t, result in history if result == 'failed']
        accepted = [t for t, result in history if result == 'accepted']
        unresolved = failed and (not accepted or failed[-1] >= accepted[-1])
        # An event alone cannot clear a failure: acceptance also needs the closed
        # task's current evidence. Blocked work retains accountability without WIP.
        if failed and (unresolved or row['status'] != 'accepted'):
            require(row['status'] == 'open' and task['status'] in ('reopened', 'blocked'),
                    f'{id}: latest failure after acceptance or report requires open feedback and reopened/blocked task')
        if row['status'] == 'accepted':
            require(task['status'] == 'closed', f'{id}: accepted feedback needs closed task')
            at = (self.product_closure(task) if task['kind'] == 'product'
                  else self.time(task['closure']['at'], id))
            require(accepted and (not failed or at > failed[-1]) and accepted[-1] >= at and not unresolved,
                    f'{id}: accepted feedback needs acceptance and recheck after latest failure')
        if task['status'] == 'closed':
            require(row['status'] in ('accepted', 'waived', 'rejected'), f'{id}: closed task hides unresolved feedback')

    def parent_closure(self):
        for parent, child, key in [('projects', 'plans', 'project'), ('plans', 'tasks', 'plan')]:
            for row in self.groups[parent].values():
                if row['status'] == 'closed':
                    require(all(c['status'] == 'closed' for c in self.groups[child].values() if c[key] == row['id']),
                            f'{row["id"]}: cannot close with nonclosed {key == "project" and "plan" or "task"}')

    def check(self, data):
        require(isinstance(data, dict) and type(data.get('version')) is int and data['version'] == 1,
                'expected version-1 ledger object')
        self.inventory(data.get('sources'))
        for group in ('projects', 'plans', 'tasks', 'feedback'):
            self.entities(group, data.get(group))
        active = self.tasks()
        self.dependencies()
        self.feedback()
        self.parent_closure()
        return {'coherent': True, 'failures': [], 'product_acceptance_claimed': False,
                'as_of': self.as_of.isoformat(), 'counts': {**{g: len(rows) for g, rows in self.groups.items()},
                'source_ids': len(self.sources), 'active_tasks': sum(active.values())},
                'project_wip': dict(active), 'migration_gaps': self.gaps,
                'status_counts': {g: dict(Counter(row['status'] for row in rows.values())) for g, rows in self.groups.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--as-of', default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    parser.add_argument('--summary', action='store_true', help='omit per-entity next actions')
    args = parser.parse_args()
    ledger = None
    try:
        data = json.loads(Path(args.ledger).read_text(), object_pairs_hook=object_pairs,
                          parse_constant=lambda value: require(False, f'invalid JSON constant: {value}'))
        ledger = Ledger(args.root, args.as_of)
        result = ledger.check(data)
        if not args.summary:
            result['pending'] = [{k: row[k] for k in ('id', 'status', 'owner', 'next_action', 'review_on')}
                                 for rows in ledger.groups.values() for row in rows.values() if row['status'] not in TERMINAL]
        code = 0
    except (ValueError, OSError, UnicodeError, OverflowError, RecursionError) as error:
        result = {'coherent': False, 'product_acceptance_claimed': False, 'failures': [str(error)],
                  'counts': {g: len(rows) for g, rows in ledger.groups.items()} if ledger else {},
                  'migration_gaps': ledger.gaps if ledger else []}
        code = 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
