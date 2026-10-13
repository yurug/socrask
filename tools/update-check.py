#!/usr/bin/env python3
"""update-check — tell the agent when a newer kit release exists.

Run from a SessionStart hook (templates/settings/kit-update.settings.json). The
hook's stdout enters the agent's context, so the notice is present at session
start instead of depending on an agent remembering to look.

Usage:
    update-check.py [--kit DIR] [--remote NAME_OR_URL] [--max-age HOURS]

    --kit       kit checkout; defaults to the checkout holding this script
    --remote    where releases are tagged; defaults to `origin`
    --max-age   hours between network checks (default 24); 0 always checks

Compares the newest `vX.Y.Z` tag reachable from the checkout's HEAD with the
newest one on the remote. The remote answer is cached per checkout in
~/.cache/socrask/. Prints nothing when the kit is current, the checkout has
no release tag, or the remote cannot be reached. Always exits 0: a hook that
fails would block the session, and a missed notice only delays an update.

What this does NOT do: update anything. The notice tells the agent to propose
the update and to wait for the human's consent.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0",
               GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=5")


def version(tag):
    m = TAG_RE.match(tag)
    return tuple(int(x) for x in m.groups()) if m else ()


def git(kit, *args, timeout=10):
    result = subprocess.run(["git", "-C", str(kit), *args], capture_output=True,
                            text=True, timeout=timeout, env=GIT_ENV)
    return result.stdout if result.returncode == 0 else None


def installed(kit):
    out = git(kit, "tag", "--merged", "HEAD", "--list", "v*")
    tags = [t for t in (out or "").split() if version(t)]
    return max(tags, key=version) if tags else None


def latest_remote(kit, remote):
    out = git(kit, "ls-remote", "--tags", "--refs", remote, "v*", timeout=15)
    if out is None:
        return None
    tags = [line.split("refs/tags/", 1)[1] for line in out.splitlines() if "refs/tags/" in line]
    tags = [t for t in tags if version(t)]
    return max(tags, key=version) if tags else None


def cached_latest(kit, remote, max_age):
    key = hashlib.sha256(f"{kit}\0{remote}".encode()).hexdigest()[:16]
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "socrask" / f"update-{key}.json"
    try:
        data = json.loads(cache.read_text())
        if max_age > 0 and time.time() - data["checked"] < max_age * 3600:
            return data["latest"]
    except (OSError, ValueError, KeyError):
        pass
    latest = latest_remote(kit, remote)
    if latest is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"checked": time.time(), "latest": latest}))
        except OSError:
            pass
    return latest


def main():
    parser = argparse.ArgumentParser(description="Report a newer kit release to the agent.")
    parser.add_argument("--kit", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--max-age", type=float, default=24)
    args = parser.parse_args()
    kit = args.kit.resolve()

    current = installed(kit)
    if current is None:
        return 0
    latest = cached_latest(kit, args.remote, args.max_age)
    if latest is None or version(latest) <= version(current):
        return 0
    print(f"""Socrask kit update available: {latest} (installed: {current}, checkout: {kit}).
Propose this update to the user once in this session; do not update without consent.
Before asking, read what changed: `git -C {kit} fetch --tags {args.remote}` then
`git -C {kit} show {latest}:CHANGELOG.md`, and summarize the entries after {current},
especially their Compatibility notes.
If the user agrees: `git -C {kit} pull --ff-only {args.remote} {latest}` (it refuses
local changes or a diverged checkout: report that, do not force), then
`{kit}/sync-skills.sh --check`, then re-read the skills this session uses.
A project that pins a kit commit (`--expected-revision`) must also update the pin,
in its own commit.""")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 -- a session-start hook must never block the session
        sys.exit(0)
