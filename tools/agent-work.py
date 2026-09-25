#!/usr/bin/env python3
"""Coordinate cooperating agents in worktrees of one local Git repository.

Claims are advisory, durable and serialized in the common Git directory. They
are not a security boundary. No TTL steals work from a slow or disconnected agent.
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import socket
import signal
import subprocess
import sys
import tempfile
import time


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def write(path, data):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.state-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def transaction(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / 'state.json'
        state = json.loads(path.read_text()) if path.exists() else {'tasks': {}, 'resources': {}}
        yield state
        write(path, state)


def normalized(value):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not path.parts or any(c in value for c in '*?['):
        raise ValueError('paths must be literal repository-relative files or directories')
    if path.parts[0] == '.git':
        raise ValueError('Git metadata cannot be claimed')
    return path.as_posix().rstrip('/')


def overlaps(a, b):
    return a == b or a.startswith(b + '/') or b.startswith(a + '/')


def task_for(state, args, worktree):
    task = state['tasks'].get(args.task)
    if not task or task['status'] == 'closed':
        raise ValueError('no active task with that ID')
    if task['owner'] != args.owner or task['worktree'] != worktree:
        raise ValueError('task belongs to another owner or worktree')
    return task


def clean():
    return not git('status', '--porcelain', '--untracked-files=all')


def changed(base):
    tracked = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', '-z', base], text=True)
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], text=True)
    return set(filter(None, (tracked + untracked).split('\0')))


def scope(task, state):
    paths = list(task['paths'])
    if task['role'] == 'coordinator':
        for child in state['tasks'].values():
            if child.get('coordinator') == task['id'] and child['status'] == 'ready':
                if subprocess.run(['git', 'merge-base', '--is-ancestor', child['head'], 'HEAD']).returncode == 0:
                    paths.extend(child['paths'])
    outside = sorted(p for p in changed(task['base']) if not any(overlaps(p, own) and (p == own or p.startswith(own + '/')) for own in paths))
    if outside:
        raise ValueError('changes outside owned paths: ' + ', '.join(outside))


def alignment(record, stage, base, head=None, work_id=None, tier=None):
    command = [sys.executable, str(Path(__file__).with_name('alignment-check.py')),
               str(Path(record).resolve()), '--stage', stage, '--base', base]
    if head:
        command += ['--head', head]
    if subprocess.run(command).returncode:
        raise ValueError('alignment checkpoint is not settled; technical work is not human completion')
    data = json.loads(Path(record).read_text())
    if work_id is not None and data['work_id'] != work_id:
        raise ValueError('alignment record belongs to another work_id')
    if tier is not None and data['tier'] != tier:
        raise ValueError('alignment tier changed; create a new scoped task instead of downgrading closure')
    return data


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='action', required=True)
    sub.add_parser('status')
    for command in ('claim', 'check', 'run', 'handoff', 'close'):
        p = sub.add_parser(command)
        p.add_argument('--task', required=True)
        p.add_argument('--owner', required=True)
        if command == 'claim':
            p.add_argument('--path', action='append', required=True)
            p.add_argument('--base', default='HEAD')
            p.add_argument('--criteria', required=True)
            p.add_argument('--role', choices=['coordinator', 'worker'], default='coordinator')
            p.add_argument('--alignment')
            p.add_argument('--coordinator')
        if command == 'run':
            p.add_argument('--resource', action='append', default=[])
            p.add_argument('command', nargs=argparse.REMAINDER)
        if command == 'close':
            p.add_argument('--reason', required=True)
            p.add_argument('--outcome', choices=['integrated', 'abandoned'], required=True)
            p.add_argument('--alignment')
    recover = sub.add_parser('recover-task')
    recover.add_argument('--task', required=True)
    recover.add_argument('--reason', required=True)
    return ap


def main():
    args = parser().parse_args()
    worktree = git('rev-parse', '--show-toplevel')
    os.chdir(worktree)
    root = Path(git('rev-parse', '--path-format=absolute', '--git-common-dir')) / 'agentic-loop'
    if args.action == 'status':
        with transaction(root) as state:
            print(json.dumps(state, indent=2))
        return 0
    if args.action == 'recover-task':
        with transaction(root) as state:
            task = state['tasks'].get(args.task, {})
            lease = task.get('running')
            if not lease or lease['host'] != socket.gethostname():
                raise ValueError('recovery needs a recorded command on this host')
            for pid, group in [(lease['pid'], False), (lease['child'], True)]:
                try:
                    (os.killpg if group else os.kill)(pid, 0)
                except ProcessLookupError:
                    pass
                else:
                    raise ValueError('command supervisor or process group still exists')
            if len(args.reason.strip()) < 10:
                raise ValueError('recovery needs a meaningful reason')
            state.setdefault('recoveries', []).append({**lease, 'task': args.task, 'reason': args.reason})
            state['resources'] = {r: v for r, v in state['resources'].items() if v['task'] != args.task}
            task.pop('running')
            task['checks'].append({'exit': 130, 'commit': None, 'recovered': args.reason})
        return 0
    with transaction(root) as state:
        if args.action == 'claim':
            if args.task in state['tasks']:
                raise ValueError('task ID already exists; use a new ID')
            branch = git('symbolic-ref', '--quiet', '--short', 'HEAD')
            base = git('rev-parse', '--verify', args.base + '^{commit}')
            if subprocess.run(['git', 'merge-base', '--is-ancestor', base, 'HEAD']).returncode:
                raise ValueError('base must be an ancestor of HEAD')
            paths = sorted(set(normalized(p) for p in args.path))
            if args.role == 'coordinator':
                if not args.alignment:
                    raise ValueError('coordinator requires --alignment; see docs/alignment.md')
                record = alignment(args.alignment, 'start', base, work_id=args.task)
            else:
                coordinator = state['tasks'].get(args.coordinator, {})
                if coordinator.get('role') != 'coordinator' or coordinator.get('status') != 'active':
                    raise ValueError('worker requires an active --coordinator task')
            for other in state['tasks'].values():
                if other['status'] == 'closed':
                    continue
                if other['worktree'] == worktree:
                    raise ValueError('one active writing task per worktree; create a separate worktree')
                if any(overlaps(a, b) for a in paths for b in other['paths']):
                    raise ValueError('owned path overlaps task ' + other['id'])
            state['tasks'][args.task] = dict(id=args.task, owner=args.owner, paths=paths, base=base,
                branch=branch, worktree=worktree, criteria=args.criteria, status='active', checks=[],
                role=args.role, coordinator=args.coordinator, tier=record['tier'] if args.role == 'coordinator' else None)
            print('claimed ' + args.task)
            return 0
        task = task_for(state, args, worktree)
        if args.action == 'close':
            if any(r['task'] == args.task for r in state['resources'].values()) or task.get('running'):
                raise ValueError('cannot close while a command or resource is active')
            if len(args.reason.strip()) < 10:
                raise ValueError('closure needs integration evidence or an abandonment reason')
            if args.outcome == 'integrated':
                if task['status'] != 'ready':
                    raise ValueError('integration requires a ready handoff first')
                if not clean() or git('rev-parse', 'HEAD') != task['head']:
                    raise ValueError('closure must use the clean, tested handoff commit')
                if task['role'] == 'coordinator':
                    pending = [c for c in state['tasks'].values() if c.get('coordinator') == task['id'] and c['status'] != 'closed']
                    if any(c['status'] != 'ready' or subprocess.run(['git', 'merge-base', '--is-ancestor', c['head'], 'HEAD']).returncode for c in pending):
                        raise ValueError('all workers must be ready and included in integration')
                    if not args.alignment:
                        raise ValueError('coordinator closure requires --alignment finish evidence')
                    alignment(args.alignment, 'finish', task['base'], git('rev-parse', 'HEAD'), args.task, task['tier'])
                else:
                    coordinator = state['tasks'].get(task['coordinator'], {})
                    if coordinator.get('outcome') != 'integrated':
                        raise ValueError('coordinator must close integration first')
            task.update(status='closed', closure=args.reason, outcome=args.outcome)
            return 0
        scope(task, state)
        if args.action == 'check':
            print('scope holds for ' + args.task)
            return 0
        if task.get('running'):
            raise ValueError('task already has a running command')
        if args.action == 'handoff':
            sha = git('rev-parse', 'HEAD')
            if not clean() or not task['checks'] or task['checks'][-1]['exit'] != 0 or task['checks'][-1]['commit'] != sha:
                raise ValueError('handoff needs a clean tree and a successful run on current HEAD')
            task.update(status='ready', head=sha)
            print(json.dumps(task, indent=2))
            return 0
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        if not command:
            raise ValueError('run needs a command after --')
        if task['status'] != 'active':
            raise ValueError('ready tasks cannot run; close and claim a new task for revisions')
        if any(r in state['resources'] for r in args.resource):
            raise ValueError('a requested resource is held; inspect status')
        sha = git('rev-parse', 'HEAD') if clean() else None
        # The child cannot execute user code before its lease is durable. EOF
        # means the supervisor died or persistence failed: exit without exec.
        read_fd, go_fd = os.pipe()
        bootstrap = 'import os,sys; fd=int(sys.argv[1]); go=os.read(fd,1); os.close(fd); (os.execvp(sys.argv[2],sys.argv[2:]) if go==b"1" else sys.exit(125))'
        child = subprocess.Popen([sys.executable, '-c', bootstrap, str(read_fd), *command],
                                 pass_fds=(read_fd,), start_new_session=True)
        os.close(read_fd)
        task['running'] = {'pid': os.getpid(), 'host': socket.gethostname(), 'child': child.pid}
        for resource in args.resource:
            state['resources'][resource] = dict(task=args.task, **task['running'])
    # Do not hold the registry mutex while executing tests; unrelated tasks continue.
    os.write(go_fd, b'1')
    os.close(go_fd)
    start = time.monotonic()
    try:
        result = child.wait()
    except (OSError, KeyboardInterrupt) as exc:
        print(str(exc), file=sys.stderr)
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        result = 130 if isinstance(exc, KeyboardInterrupt) else 127
    with transaction(root) as state:
        task = task_for(state, args, worktree)
        if not clean() or git('rev-parse', 'HEAD') != sha:
            sha = None
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            descendants = False
        else:
            descendants = True
            print('agent-work: descendants still exist; resource lease retained for recovery', file=sys.stderr)
            result = 2
        task['checks'].append(dict(command=command, exit=result, commit=sha,
                                   seconds=round(time.monotonic() - start, 3)))
        if not descendants:
            task.pop('running', None)
            for resource in set(args.resource):
                del state['resources'][resource]
    return result if result >= 0 else 128 - result


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('agent-work: ' + str(exc), file=sys.stderr)
        sys.exit(2)
