#!/usr/bin/env python3
"""Disposable-repository enrollment integration checks. Run with Python 3."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

KIT = Path(__file__).resolve().parent.parent
ENROLL = KIT / 'tools/enroll-shared-repo.sh'
GUARD = KIT / 'tools/guard-kit-artifacts.sh'

def run(*args, ok=True, input=None):
    p = subprocess.run([str(a) for a in args], input=input, text=True, capture_output=True)
    assert (p.returncode == 0) == ok, (args, p.returncode, p.stdout, p.stderr)
    return p.stdout

def git(repo, *args):
    return run('git', '-C', repo, *args)

def init(path):
    path.mkdir()
    git(path, 'init', '-q')
    git(path, 'config', 'user.email', 'test@example.invalid')
    git(path, 'config', 'user.name', 'Enrollment Test')
    git(path, 'commit', '--allow-empty', '-qm', 'base')
    return path

def enroll(repo, side, ok=True):
    return run(ENROLL, repo, '--sidecar', side, ok=ok)

with tempfile.TemporaryDirectory(prefix='kit enrollment ') as td:
    root = Path(td)
    repo = init(root / "repo ' quoted")
    side = root / "side ' quoted"
    (repo / 'kb').mkdir()
    (repo / 'kb/note').write_text('personal')
    enroll(repo, side)
    settings = (repo / '.claude/settings.local.json').read_bytes()
    enroll(repo, side)
    assert settings == (repo / '.claude/settings.local.json').read_bytes()
    assert (side / 'kb/note').read_text() == 'personal'
    assert (repo / '.inbrief').is_symlink() and (side / '.inbrief').is_dir()
    assert not git(repo, 'status', '--porcelain')
    command = json.loads(settings)['hooks']['SessionStart'][0]['hooks'][0]['command']
    assert json.loads(run('sh', '-c', command))['hookSpecificOutput']['hookEventName'] == 'SessionStart'
    for force in ('-f', '--force', '-Af'):
        run(GUARD, '--hook', repo, input=json.dumps({'tool_input': {'command': 'git add ' + force + ' kb'}}), ok=False)
    run(GUARD, '--staged', repo)
    git(repo, 'add', '-f', 'kb')
    run(GUARD, '--staged', repo, ok=False)
    enroll(repo, side, ok=False)
    run(GUARD, '--staged', repo, ok=False)
    git(repo, 'reset', '-q')
    enroll(repo, root / 'different', ok=False)
    assert not (root / 'different').exists()

    # Team-owned directory, missing tracked file and symlink stay untouched.
    repo = init(root / 'tracked')
    (repo / 'kb').mkdir()
    (repo / 'kb/team').write_text('team')
    (repo / 'SESSION_STATE.md').write_text('team')
    (repo / '.forebrief').symlink_to('kb')
    (repo / '.claude').mkdir()
    settings = repo / '.claude/settings.local.json'
    settings.write_text('{"team": true}')
    git(repo, 'add', '-f', 'kb', 'SESSION_STATE.md', '.forebrief', '.claude/settings.local.json')
    git(repo, 'commit', '-qm', 'team files')
    (repo / 'SESSION_STATE.md').unlink()
    before = git(repo, 'status', '--porcelain')
    enroll(repo, root / 'tracked-side')
    assert git(repo, 'status', '--porcelain') == before
    assert settings.read_text() == '{"team": true}'
    assert not (repo / 'SESSION_STATE.md').exists()
    assert os.readlink(repo / '.forebrief') == 'kb'
    assert not (repo / 'kb').is_symlink()

    settings.unlink()
    enroll(repo, root / 'tracked-side')
    assert not settings.exists()

    repo = init(root / 'foreign')
    (repo / 'kb').symlink_to(root / 'missing-foreign')
    enroll(repo, root / 'foreign-side')
    assert os.readlink(repo / 'kb') == str(root / 'missing-foreign')
    assert not (root / 'foreign-side/kb').exists()

    repo = init(root / 'settings-symlink')
    (repo / '.claude').mkdir()
    foreign = root / 'foreign-settings.json'
    foreign.write_text('{}')
    (repo / '.claude/settings.local.json').symlink_to(foreign)
    enroll(repo, root / 'settings-side')
    assert foreign.read_text() == '{}'
    assert (repo / '.claude/settings.local.json').is_symlink()

    # Expected failures happen before moving even the first artifact.
    for case in ('invalid-json', 'conflict', 'side-link', 'nested', 'bad-hooks'):
        repo = init(root / case)
        (repo / 'kb').mkdir()
        side = root / (case + '-side')
        if case in ('invalid-json', 'bad-hooks'):
            (repo / '.claude').mkdir()
            (repo / '.claude/settings.local.json').write_text('{' if case == 'invalid-json' else '{"hooks":{"SessionStart":42}}')
        elif case == 'conflict':
            side.mkdir()
            (side / 'kb').mkdir()
        elif case == 'side-link':
            side.mkdir()
            (side / 'kb').symlink_to(root / 'missing')
        elif case == 'nested':
            side = repo / 'side'
        enroll(repo, side, ok=False)
        assert (repo / 'kb').is_dir() and not (repo / 'kb').is_symlink()
        assert not (repo / '.forebrief').exists()

    # Concurrent startup serializes before reading ownership or moving content.
    repo = init(root / 'concurrent')
    side = root / 'concurrent-side'
    (repo / 'kb').mkdir()
    (repo / 'kb/personal').write_text('preserved')
    procs = [subprocess.Popen([str(ENROLL), str(repo), '--sidecar', str(side)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
    for proc in procs:
        out, err = proc.communicate(timeout=20)
        assert proc.returncode == 0, (out, err)
    assert (side / 'kb/personal').read_text() == 'preserved'
    assert not git(repo, 'status', '--porcelain')
    settings = json.loads((repo / '.claude/settings.local.json').read_text())
    assert len(settings['hooks']['SessionStart']) == 1
    assert len(settings['hooks']['PreToolUse']) == 1

    main = init(root / 'main')
    wt = root / 'linked worktree'
    git(main, 'worktree', 'add', '-qb', 'work', wt)
    enroll(wt, root / 'worktree-side')
    enroll(wt, root / 'worktree-side')
    assert not git(wt, 'status', '--porcelain')
    run(GUARD, '--staged', wt)
    git(wt, 'add', '-f', 'SESSION_STATE.md')
    run(GUARD, '--staged', wt, ok=False)
    run(GUARD, '--staged', main)
print('Enrollment integration checks passed')
