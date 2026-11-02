#!/usr/bin/env python3
"""ledger — read and change the work ledger one entry at a time.

The ledger (`kb/work/ledger.json`, contract in docs/project-management.md) grows
to hundreds of entries. Without this tool, an agent writes a Python script for
each change: load the file, find the entry, set a field, write the file back.
That costs about 1,500 generated characters per change, and each script can
reformat the file or skip validation. With it, a change is one short command,
and the ledger is validated before it is written.

Usage (from the project root):
    ledger.py get ID                          the entry, as one line of JSON
    ledger.py list [GROUP] [--status S]... [--owner O] [--due DATE] [--archived]
                                              one line per entry: id, status, owner,
                                              review_on, next_action
    ledger.py set ID FIELD=VALUE...           change fields; a dotted FIELD
                                              (closure.at) sets a nested field
    ledger.py add GROUP JSON                  add an entry to projects, plans,
                                              tasks or feedback
    ledger.py event ID --result failed|accepted --ref PATH [--at TIME]
                                              append an observation to feedback ID
    ledger.py archive                         move finished entries to the archive

    --ledger   defaults to kb/work/ledger.json; the archive is
               kb/work/ledger-archive.json (project-check.py reads both)
    --root     defaults to .; references resolve against it
    --as-of    the review date for validation; defaults to today

A VALUE that parses as JSON (a list, a number, an object) is stored as that
JSON, and `@PATH` reads the JSON from a file; any other VALUE is a string.

Every write validates the ledger with project-check.py's rules, archive
included. It refuses a write that makes a coherent ledger incoherent, and
names the rule. When the ledger was already incoherent, it writes and prints
the remaining failure, so that fixes can land one at a time. It keeps the
file's indentation and key order, and replaces the file atomically.

`archive` moves an entry only when the move cannot change a verdict: a closed
task whose feedback is all finished, that feedback, and a closed plan or
project whose children are all archived.

Exit code: 0 = done, 1 = refused (unknown ID, bad field, a write that breaks
the ledger), 2 = unreadable ledger.

What this does NOT do: lock the file against a concurrent writer in the same
worktree (one worktree per agent, see agent-work.py), or check that a
next_action is meaningful.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

GROUPS = ('projects', 'plans', 'tasks', 'feedback')


def project_check():
    """The ledger's rules live in one place: project-check.py."""
    spec = importlib.util.spec_from_file_location('project_check', Path(__file__).with_name('project-check.py'))
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(__file__).parent))  # project-check imports project_history
    spec.loader.exec_module(module)
    return module


PC = project_check()


class Refused(Exception):
    pass


def indent_of(path):
    """The file's own indentation, so a write changes only the lines it must."""
    for line in Path(path).read_text(encoding='utf-8').splitlines()[1:2]:
        return len(line) - len(line.lstrip(' ')) or 2
    return 2


def dump(path, data, indent):
    text = json.dumps(data, indent=indent, ensure_ascii=False) + '\n'
    fd, tmp = tempfile.mkstemp(dir=Path(path).parent, prefix='.ledger-')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def verdict(data, archive, root, as_of):
    """None when coherent, else the first failure, as project-check.py states it."""
    try:
        PC.Ledger(root, as_of).check(PC.with_archive(data, archive))
        return None
    except ValueError as error:
        return str(error)


def find(data, id):
    for group in GROUPS:
        for row in data.get(group, []):
            if row.get('id') == id:
                return group, row
    raise Refused(f'unknown ID: {id}')


def value(text):
    if text.startswith('@'):
        return PC.read_json(text[1:])
    try:
        return json.loads(text)
    except ValueError:
        return text


def assign(row, field, new):
    *path, last = field.split('.')
    if field == 'id':
        raise Refused('the id is the entry\'s identity; add a new entry instead')
    for key in path:
        row = row.setdefault(key, {})
        if not isinstance(row, dict):
            raise Refused(f'{field}: {key} is not an object')
    row[last] = new


def line(row):
    action = ' '.join(str(row.get('next_action', '')).split())
    action = action if len(action) <= 100 else action[:99] + '…'
    return '\t'.join(str(row.get(k, '')) for k in ('id', 'status', 'owner', 'review_on')) + '\t' + action


def archive_entries(data, archive):
    """Move what is finished and can no longer change a verdict."""
    moved = {g: [] for g in GROUPS}
    feedback_of = {}
    for row in data['feedback']:
        feedback_of.setdefault(row.get('task'), []).append(row)
    for task in data['tasks']:
        rows = feedback_of.get(task['id'], [])
        if task.get('status') == 'closed' and all(r.get('status') in PC.TERMINAL for r in rows):
            moved['tasks'].append(task)
            moved['feedback'] += rows
    for parent, child, key in (('plans', 'tasks', 'plan'), ('projects', 'plans', 'project')):
        live = {r.get(key) for r in data[child] if r not in moved[child]}
        moved[parent] = [r for r in data[parent] if r.get('status') == 'closed' and r['id'] not in live]
    for group in GROUPS:
        ids = {id(r) for r in moved[group]}
        data[group] = [r for r in data[group] if id(r) not in ids]
        archive.setdefault(group, []).extend(moved[group])
    return sum(len(rows) for rows in moved.values())


def main():
    ap = argparse.ArgumentParser(description='Read and change the work ledger one entry at a time.')
    ap.add_argument('--ledger', default='kb/work/ledger.json')
    ap.add_argument('--root', default='.')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('get').add_argument('id')
    ls = sub.add_parser('list')
    ls.add_argument('group', nargs='?', choices=GROUPS)
    ls.add_argument('--status', action='append')
    ls.add_argument('--owner')
    ls.add_argument('--due', help='review_on on or before this YYYY-MM-DD date')
    ls.add_argument('--archived', action='store_true', help='include archived entries')
    st = sub.add_parser('set')
    st.add_argument('id')
    st.add_argument('assignments', nargs='+', metavar='FIELD=VALUE')
    ad = sub.add_parser('add')
    ad.add_argument('group', choices=GROUPS)
    ad.add_argument('entry', help='JSON object, or @PATH')
    ev = sub.add_parser('event')
    ev.add_argument('id')
    ev.add_argument('--result', required=True, choices=('failed', 'accepted'))
    ev.add_argument('--ref', required=True)
    ev.add_argument('--at', default=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'))
    sub.add_parser('archive')
    args = ap.parse_args()

    path, apath = Path(args.ledger), PC.archive_path(args.ledger)
    try:
        data = PC.read_json(path)
        archive = PC.read_json(apath) if apath.is_file() else None
    except (OSError, ValueError) as error:
        print(f'ledger: cannot read {path}: {error}')
        return 2
    try:
        if args.cmd == 'get':
            merged = PC.with_archive(data, archive)
            print(json.dumps(find(merged, args.id)[1], ensure_ascii=False))
            return 0
        if args.cmd == 'list':
            merged = PC.with_archive(data, archive) if args.archived else data
            rows = [r for g in ([args.group] if args.group else GROUPS) for r in merged.get(g, [])]
            rows = [r for r in rows if (not args.status or r.get('status') in args.status)
                    and (not args.owner or r.get('owner') == args.owner)
                    and (not args.due or str(r.get('review_on', '9999')) <= args.due)]
            for r in rows:
                print(line(r))
            print(f'ledger: {len(rows)} entries')
            return 0

        before = verdict(data, archive, args.root, args.as_of)
        if args.cmd == 'set':
            _, row = find(data, args.id)
            for a in args.assignments:
                field, sep, text = a.partition('=')
                if not sep or not field:
                    raise Refused(f'expected FIELD=VALUE, got {a}')
                assign(row, field, value(text))
            done = f'set {args.id} ' + ', '.join(a.split('=', 1)[0] for a in args.assignments)
        elif args.cmd == 'add':
            entry = value(args.entry)
            if not isinstance(entry, dict) or not entry.get('id'):
                raise Refused('the entry must be a JSON object with an id')
            merged = PC.with_archive(data, archive)
            if any(r.get('id') == entry['id'] for g in GROUPS for r in merged.get(g, [])):
                raise Refused(f'duplicate ID: {entry["id"]}')
            data.setdefault(args.group, []).append(entry)
            done = f'added {entry["id"]} to {args.group}'
        elif args.cmd == 'event':
            group, row = find(data, args.id)
            if group != 'feedback':
                raise Refused(f'{args.id} is in {group}; events belong to feedback')
            row.setdefault('events', []).append({'at': args.at, 'result': args.result, 'ref': args.ref})
            done = f'{args.id}: {args.result} event at {args.at}'
        else:
            archive = archive or {'version': 1}
            done = f'archived {archive_entries(data, archive)} entries to {apath}'

        after = verdict(data, archive, args.root, args.as_of)
        if after and not before:
            raise Refused(f'the ledger would become incoherent: {after}')
        dump(path, data, indent_of(path))
        if args.cmd == 'archive':
            dump(apath, archive, indent_of(path))
        print(f'ledger: {done}' + (f'; still incoherent: {after}' if after else ''))
        return 0
    except Refused as error:
        print(f'ledger: refused: {error}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
