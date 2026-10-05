"""Preserve committed observations when the work ledger changes.

Purpose: Refuse loss of feedback observations already committed after a trusted rollout.
Owns: read-only Git traversal and ordered retention of historical feedback IDs/events.
Does not own: current ledger validity or outcome acceptance (project-check.py).
Interface: check_history(root, ledger_path, base, data, raw) returns a history receipt;
raises ValueError/OSError for invalid or unavailable history. Reads Git objects only.
Invariants: HEAD is pinned once; every selected prior event survives whole and in order.
Old snapshots validate structure, never present-day review dates or files on disk.
Dependencies: Git supplies committed snapshots; JSON identifies entire events; SHA-256
identifies the exact current ledger bytes. Contract: docs/project-management.md.

Duplicate multiplicity is preserved within each snapshot. Without event IDs this
cannot distinguish byte-identical independent events introduced on separate branches.
The caller chooses a trustworthy baseline; this gate cannot authenticate evidence.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def _require(condition, message):
    if not condition:
        raise ValueError('history: ' + message)


def _string(value):
    return isinstance(value, str) and bool(value.strip())


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _event(record, label):
    """Validate structural evidence, returning its instant and lossless JSON identity."""
    _require(isinstance(record, dict), f'{label}: event must be an object')
    _require(record.get('result') in ('failed', 'accepted'), f'{label}: invalid event result')
    _require(_string(record.get('at')), f'{label}: event timestamp required')
    instant = dt.datetime.fromisoformat(record['at'].replace('Z', '+00:00'))
    _require(instant.tzinfo is not None, f'{label}: event timestamp needs timezone')
    ref = record.get('ref')
    _require(_string(ref), f'{label}: event reference required')
    path = ref.split('#', 1)[0]
    # Do not resolve old references against today's filesystem: files may have moved.
    _require(path and not Path(path).is_absolute() and '://' not in path
             and '..' not in Path(os.path.normpath(path)).parts,
             f'{label}: event needs relative local reference')
    return instant, json.dumps(record, sort_keys=True, allow_nan=False)


def _feedback(data):
    """Extract immutable observations; ownership, task mappings and dispositions may change."""
    _require(isinstance(data, dict) and type(data.get('version')) is int
             and data['version'] == 1, 'expected version-1 ledger object')
    _require(isinstance(data.get('feedback'), list), 'feedback array required')
    result = {}
    for row in data['feedback']:
        _require(isinstance(row, dict) and _string(row.get('id')), 'feedback ID required')
        label = row['id']
        _require(label not in result, f'duplicate feedback ID: {label}')
        _require(isinstance(row.get('events'), list), f'{label}: events array required')
        observations = [_event(record, label) for record in row['events']]
        times = [at for at, _ in observations]
        _require(times == sorted(times), f'{label}: events must be chronological')
        result[label] = [identity for _, identity in observations]
    return result


class _Repository:
    """One explicit worktree, sanitized Git environment and immutable traversal endpoint."""

    def __init__(self, root, path, base):
        lexical_root = Path(os.path.abspath(root))
        self.root = lexical_root.resolve()
        # Repository-local Git variables can silently redirect even commands with -C.
        self.env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        self.env.update(LC_ALL='C', GIT_NO_LAZY_FETCH='1')
        _require(isinstance(base, str) and re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', base),
                 'trusted base must be a full 40- or 64-hex commit ID')
        self.base = base.lower()
        repo_root = Path(self.git('rev-parse', '--show-toplevel').strip()).resolve()
        path = Path(os.path.abspath(path))
        _require(path.is_relative_to(lexical_root), 'ledger outside root')
        path = self.root / path.relative_to(lexical_root)
        # Following an alias here would compare a different file's historical ledger.
        _require(path == path.resolve(), 'ledger path must not traverse a symlink')
        _require(path.is_relative_to(repo_root), 'ledger outside root')
        self.path = path.relative_to(repo_root).as_posix()
        self.root = repo_root
        self.head = self.git('rev-parse', '--verify', 'HEAD^{commit}').strip()
        _require(self.git('rev-parse', '--is-shallow-repository').strip() == 'false',
                 'shallow repository cannot establish complete history')
        grafts = Path(self.git('rev-parse', '--git-path', 'info/grafts').strip())
        if not grafts.is_absolute():
            grafts = self.root / grafts
        _require(not grafts.exists() or grafts.stat().st_size == 0, 'nonempty info/grafts is unsupported')
        _require(self.git('cat-file', '-t', self.base).strip() == 'commit', 'trusted base must name a commit')
        _require(self.ancestor(self.base, self.head), 'trusted base must be an ancestor of pinned HEAD')

    def git(self, *args, ancestor=False):
        """Return Git output or fail closed; ancestor's exit 1 is an ordinary negative."""
        run = subprocess.run(['git', '--no-replace-objects', '--literal-pathspecs', '-C', str(self.root), *args],
                             cwd=self.root, env=self.env, capture_output=True)
        if ancestor and run.returncode == 1:
            return False
        _require(run.returncode == 0, f'Git {args[0]} unavailable: {run.stderr.decode(errors="replace").strip()}')
        return True if ancestor else run.stdout.decode('utf-8')

    def ancestor(self, older, newer):
        return self.git('merge-base', '--is-ancestor', older, newer, ancestor=True)

    def blob(self, commit):
        """Distinguish an absent path from unreadable/corrupt tree data."""
        entry = self.git('ls-tree', '-z', commit, '--', self.path)
        if not entry:
            _require(commit != self.base, 'ledger missing at trusted base')
            # A branch forked before adoption need not contain the ledger at all.
            _require(not self.ancestor(self.base, commit), f'ledger missing in history at {commit}')
            return None
        metadata, name = entry.rstrip('\0').split('\t', 1)
        mode, kind, oid = metadata.split()
        _require(name == self.path and kind == 'blob' and mode in ('100644', '100755'),
                 f'ledger must be a regular blob at {commit}')
        return oid


def _preserved(previous, current, commit):
    """Greedy ordered matching preserves each historical occurrence, including duplicates."""
    for label, old in previous.items():
        _require(label in current, f'{commit}: removed feedback ID: {label}')
        available = iter(current[label])
        for identity in old:
            _require(any(candidate == identity for candidate in available),
                     f'{commit}: {label}: removed, changed or reordered event')


def check_history(root, ledger_path, base, data, raw):
    """Return history receipt for current parsed data/raw bytes, or raise ValueError/OSError.

    The caller supplies its trusted full commit ID and the exact bytes it validated.
    @invariant T-PM-HISTORY: every selected prior feedback ID/event survives current data.
    """
    repository = _Repository(root, ledger_path, base)
    current = _feedback(data)
    # Full history retains both sides and merge-created states even if HEAD selected
    # one parent's ledger. BASE..HEAD includes merged branches forked before BASE.
    commits = [repository.base] + repository.git('rev-list', '--full-history',
        f'{repository.base}..{repository.head}', '--', repository.path).splitlines()
    seen = set()
    for commit in commits:
        blob = repository.blob(commit)
        if blob is None or blob in seen:
            continue
        try:
            old = json.loads(repository.git('show', blob), object_pairs_hook=_pairs,
                             parse_constant=lambda value: _require(False, f'invalid JSON constant: {value}'))
            _preserved(_feedback(old), current, commit)
        except (ValueError, OverflowError, RecursionError) as error:
            raise ValueError(f'history at {commit}: {error}') from error
        seen.add(blob)
    return {'checked': True, 'trusted_base': repository.base, 'resolved_head': repository.head,
            'snapshot_count': len(seen), 'current_ledger': {'path': repository.path,
            'sha256': hashlib.sha256(raw).hexdigest()}}
