#!/usr/bin/env python3
"""Install/check selected kit skill links for Claude and Codex, preserving foreign data.

Preflight the whole selection before changing anything. --replace-links is explicit;
real files/directories are never replaced. The shell entrypoint preserves the legacy target.
"""
import argparse
import os
from pathlib import Path
import sys
import uuid


def directory_conflict(directory):
    """Missing directories are creatable; broken links and file ancestors are not."""
    for path in (directory, *directory.parents):
        if path.is_symlink() and not path.exists():
            return f'dangling destination link: {path}'
        if path.exists() and not path.is_dir():
            return f'destination ancestor is not a directory: {path}'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['claude', 'codex', 'both'], default='claude')
    parser.add_argument('--only', action='append', help='install/check this skill; repeat for several')
    parser.add_argument('--claude-dir', type=Path, default=Path.home()/'.claude/skills')
    parser.add_argument('--codex-dir', type=Path, default=Path.home()/'.codex/skills')
    parser.add_argument('--check', action='store_true', help='read-only verification; nonzero on drift')
    parser.add_argument('--replace-links', action='store_true', help='explicitly retarget selected foreign symlinks')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]/'skills'
    available = {p.name: p.resolve() for p in source.iterdir() if p.is_dir() and (p/'SKILL.md').is_file()}
    names = sorted(set(args.only or available))
    missing = set(names)-set(available)
    if missing or not names:
        print(f'Unknown/empty skill selection: {sorted(missing)}', file=sys.stderr)
        return 2
    targets = [('claude', args.claude_dir), ('codex', args.codex_dir)]
    plan, errors = [], []
    for host, directory in targets:
        if args.target not in (host, 'both'):
            continue
        conflict = directory_conflict(directory)
        if conflict:
            errors.append(f'{host}: {conflict}')
            continue
        for name in names:
            dst, src = directory/name, available[name]
            if dst.is_symlink() and dst.resolve() == src:
                print(f'OK {host} {name} -> {src}')
            elif dst.is_symlink():
                if args.check or not args.replace_links:
                    errors.append(f'{host} {name}: foreign link (use --replace-links deliberately): {dst}')
                else:
                    plan.append((host, src, dst))
            elif dst.exists():
                errors.append(f'{host} {name}: preserve existing file/directory: {dst}')
            elif args.check:
                errors.append(f'{host} {name}: missing link: {dst}')
            else:
                plan.append((host, src, dst))
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    for host, src, dst in plan:
        dst.parent.mkdir(parents=True, exist_ok=True)
        temporary = dst.with_name('.'+dst.name+'-'+uuid.uuid4().hex)
        try:
            temporary.symlink_to(src, target_is_directory=True)
            if dst.exists() and not dst.is_symlink():
                raise OSError(f'destination changed during installation: {dst}')
            os.replace(temporary, dst)
            print(f'LINK {host} {dst.name} -> {src}')
        finally:
            temporary.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except OSError as error:
        print(f'skill installation failed: {error}', file=sys.stderr)
        sys.exit(1)
