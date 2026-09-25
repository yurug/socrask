#!/bin/sh
# Explicit index boundary plus a deliberately limited Claude Bash hook.
set -eu
exec python3 -c '
import json, pathlib, re, shlex, subprocess, sys
mode = sys.argv[1] if len(sys.argv) > 1 else "--hook"
repo = sys.argv[2] if len(sys.argv) > 2 else "."
if mode not in ("--hook", "--staged"):
    sys.exit("usage: guard-kit-artifacts.sh [--staged|--hook] [REPO]")
def git(*args):
    return subprocess.check_output(["git", "-C", repo, *args], stderr=subprocess.DEVNULL)
try:
    state = pathlib.Path(git("rev-parse", "--path-format=absolute", "--git-path", "agentic-kit.json").decode().strip())
except subprocess.CalledProcessError:
    sys.exit(0 if mode == "--hook" else 1)
if not state.exists():
    sys.exit(0)
try:
    owned = json.loads(state.read_text())["owned"]
    staged = git("diff", "--cached", "--name-only", "--no-renames", "-z").decode().split("\0")
    bad = [n for n in staged if any(n == p or n.startswith(p + "/") for p in owned)]
    reason = "personal paths are staged: " + ", ".join(bad) if bad else ""
    if mode == "--hook" and not reason:
        data = json.load(sys.stdin)
        command = data.get("tool_input", {}).get("command", "")
        # A lexical convenience guard, NOT a shell parser or security boundary.
        # It intentionally blocks direct force-adds broadly, including bundles.
        words = shlex.split(command)
        if "git" in words and "add" in words and any(w == "--force" or re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", w) for w in words):
            reason = "direct git force-add in an enrolled repository"
    if reason:
        print("BLOCKED: " + reason, file=sys.stderr)
        sys.exit(2 if mode == "--hook" else 1)
except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as e:
    print("Guard could not validate: " + str(e), file=sys.stderr)
    sys.exit(2 if mode == "--hook" else 1)
' "$@"
