#!/bin/sh
# Personal, per-worktree enrollment. Requires Python 3 and Git.
set -eu
KIT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 - "$KIT" "$@" <<'PY'
import argparse, fcntl, json, os, pathlib, shlex, subprocess, sys, tempfile
P = pathlib.Path
kit = P(sys.argv[1])
p = argparse.ArgumentParser()
p.add_argument('repo', nargs='?', default=os.getcwd())
p.add_argument('--sidecar')
a = p.parse_args(sys.argv[2:])
def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])
def exists(path):
    return os.path.lexists(path)
def fail(message):
    raise ValueError(message)
try:
    repo = P(a.repo).resolve()
    repo = P(git('rev-parse', '--show-toplevel').decode().strip())
    side = P(a.sidecar).absolute() if a.sidecar else repo.with_name(repo.name + '-kit')
    side = side.resolve()
    if side == repo or repo in side.parents or side in repo.parents:
        fail('sidecar and repository must be separate, non-nested directories')
    if exists(side) and not side.is_dir():
        fail('sidecar is not a directory')
    state = P(git('rev-parse', '--path-format=absolute', '--git-path', 'agentic-kit.json').decode().strip())
    exclude = P(git('rev-parse', '--path-format=absolute', '--git-path', 'info/exclude').decode().strip())
    common = P(git('rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip())
    # Serialize enrollments across this repository and all linked worktrees,
    # since info/exclude is shared. The lock lives in Git metadata, not the tree.
    lock = (common / 'agentic-kit-enroll.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    old = json.loads(state.read_text()) if state.exists() else None
    if old and old['sidecar'] != str(side):
        fail('already enrolled with a different sidecar')
    tracked = git('ls-files', '-z').decode().split('\0')
    if old and any(t == n or t.startswith(n + '/') for t in tracked if t for n in old['owned']):
        fail('previously enrolled personal paths are tracked or staged; unstage them before enrolling again')
    def is_tracked(name):
        return any(t == name or t.startswith(name + '/') or name.startswith(t + '/') for t in tracked if t)
    names = [line.split('#', 1)[0].strip() for line in (kit / 'tools/kit-artifacts.txt').read_text().splitlines()]
    names = [n for n in names if n]
    if any('/' in n or n in ('.', '..', '.git', '.claude') for n in names):
        fail('artifact manifest requires safe top-level names')
    plan = []
    for name in names:
        link, target = repo / name, side / name
        if is_tracked(name):
            print('SKIP tracked:', name)
            continue
        if link.is_symlink():
            if not old or name not in old['owned'] or os.readlink(link) != str(target):
                print('SKIP foreign symlink:', name)
                continue
        elif exists(link) and (not link.is_file() if name.endswith('.md') else not link.is_dir()):
            fail('repository artifact has unexpected type: ' + name)
        elif exists(link) and exists(target):
            fail('path exists in both repository and sidecar: ' + name)
        if target.is_symlink():
            fail('sidecar artifact must not be a symlink: ' + name)
        if exists(target) and (target.is_file() if not name.endswith('.md') else target.is_dir()):
            fail('sidecar artifact has unexpected type: ' + name)
        plan.append(name)
    local = repo / '.claude/settings.local.json'
    settings = None
    if is_tracked('.claude/settings.local.json') or (repo / '.claude').is_symlink() or local.is_symlink():
        print('SKIP protected settings; configure hooks manually if desired')
    else:
        if exists(repo / '.claude') and not (repo / '.claude').is_dir():
            fail('.claude is not a directory')
        settings = json.loads(local.read_text()) if exists(local) else {}
        if not isinstance(settings, dict) or not isinstance(settings.get('hooks', {}), dict):
            fail('settings and hooks must be JSON objects')
        hooks = settings.setdefault('hooks', {})
        for event, entry in [
            ('SessionStart', {'hooks': [{'type': 'command', 'command': shlex.join([str(kit / 'tools/inject-profile.sh'), str(side)])}]}),
            ('PreToolUse', {'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': shlex.join([str(kit / 'tools/guard-kit-artifacts.sh'), '--hook', str(repo)])}]})
        ]:
            if not isinstance(hooks.get(event, []), list):
                fail('hook event must be an array: ' + event)
            entries = hooks.setdefault(event, [])
            if entry not in entries:
                entries.append(entry)
    if exclude.is_symlink() or (exists(exclude) and not exclude.is_file()):
        fail('exclude must be a regular file')
    if (side / 'PROFILE.md').is_symlink() or (exists(side / 'PROFILE.md') and not (side / 'PROFILE.md').is_file()):
        fail('PROFILE.md must be a regular file')
    # All predictable conflicts are checked before any mutation. I/O failures
    # are still possible; this is not a transactional filesystem operation.
    side.mkdir(parents=True, exist_ok=True)
    for name in plan:
        link, target = repo / name, side / name
        if exists(link) and not link.is_symlink():
            link.rename(target)
        if not exists(target):
            target.touch() if name.endswith('.md') else target.mkdir()
        if not link.is_symlink():
            link.symlink_to(target)
    owned = plan + (['.claude/settings.local.json'] if settings is not None else [])
    exclude.parent.mkdir(parents=True, exist_ok=True)
    text = exclude.read_text() if exclude.exists() else ''
    lines = text.splitlines()
    additions = ['/' + n for n in owned if '/' + n not in lines]
    if additions:
        with exclude.open('a') as f:
            f.write('\n# socrask personal paths\n' + '\n'.join(additions) + '\n')
    if settings is not None:
        local.parent.mkdir(exist_ok=True)
        local.write_text(json.dumps(settings, indent=2) + '\n')
    profile = side / 'PROFILE.md'
    if not profile.exists():
        profile.write_text('# Personal profile\n\nRepository instructions remain authoritative.\nPersonal kit artifacts live in this sidecar; never stage them.\n')
    with tempfile.NamedTemporaryFile(mode='w', dir=state.parent, prefix='agentic-kit-', delete=False) as f:
        f.write(json.dumps({'sidecar': str(side), 'owned': owned}, indent=2) + '\n')
        temporary_state = f.name
    os.replace(temporary_state, state)
    print('Enrolled:', repo)
    print('Before committing run:', shlex.join([str(kit / 'tools/guard-kit-artifacts.sh'), '--staged', str(repo)]))
except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as e:
    print('Enrollment failed:', e, file=sys.stderr)
    sys.exit(1)
PY
