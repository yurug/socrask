#!/usr/bin/env python3
"""scope-check — a step changes only the files that its plan declares.

An execution step in `kb/plan.md` lists its Files, and the engineer approves the
plan with that list. An agent that edits other files changes what was approved
without telling anyone: a "small fix" elsewhere, a helper moved, a test
weakened. This check compares the files that changed since the step's base
commit with the step's Files, and refuses the others.

Usage (from the repository root):
    scope-check.py PLAN --step ID --base COMMIT [--allow GLOB]...

    PLAN      the plan file, usually kb/plan.md
    --step    the step ID, as in `## Step ID: ...`
    --base    the commit where the step started (the alignment record has it)
    --allow   one more glob that any step may change (repeatable)

The changed set is every path that differs between COMMIT and the working tree,
both sides of a rename, plus the untracked files that git does not ignore.

A Files entry is the first word of each `code span` in the step's Files field:
an exact path, a directory when it ends with `/`, or a glob. Any step may also
change `kb/` (the KB changes in the same commit as the code) and `.ratchet.json`.

Exit code: 0 = every change is in scope, 1 = changes outside the scope,
2 = unusable input (no plan, no such step, no Files, unknown commit).

Checks:
    E-scope   a changed file that the step's Files do not cover. Revert it,
              or change the plan's Files with a reason, which the engineer sees

What this does NOT check: that a change inside a declared file stays within
the step's intent, or files that another process changed after COMMIT. The
review reads the diff for those.
"""

import argparse
import fnmatch
import importlib.util
from pathlib import Path
import subprocess
import sys

ALWAYS = ["kb/", ".ratchet.json"]


def plan_check():
    """The plan's grammar lives in one place: plan-check.py."""
    spec = importlib.util.spec_from_file_location("plan_check", Path(__file__).with_name("plan-check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.splitlines()


def changed(base):
    paths = set()
    for line in git("diff", "--name-status", "--no-renames", base):
        paths.add(line.split("\t", 1)[1])
    paths.update(git("ls-files", "--others", "--exclude-standard"))
    return sorted(paths)


def covers(entry, path):
    if entry.endswith("/"):
        return path.startswith(entry)
    return path == entry or fnmatch.fnmatchcase(path, entry)


def main():
    ap = argparse.ArgumentParser(description="Refuse changes outside a plan step's Files.")
    ap.add_argument("plan")
    ap.add_argument("--step", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--allow", action="append", default=[])
    args = ap.parse_args()

    pc = plan_check()
    try:
        steps = dict(pc.parse_steps(Path(args.plan).read_text(encoding="utf-8")))
    except OSError as error:
        print(f"scope-check: cannot read {args.plan}: {error}")
        return 2
    if args.step not in steps:
        print(f"scope-check: {args.plan} has no step {args.step}")
        return 2
    entries = [span.strip("`").split()[0] for span in pc.CODE_RE.findall(steps[args.step].get("files", ""))
               if span.strip("`").split()]
    if not entries:
        print(f"scope-check: step {args.step} declares no Files; plan-check.py requires them on execution steps")
        return 2
    try:
        paths = changed(args.base)
    except subprocess.CalledProcessError as error:
        print(f"scope-check: git failed: {error.stderr.strip()}")
        return 2

    allowed = entries + ALWAYS + args.allow
    outside = [p for p in paths if not any(covers(e, p) for e in allowed)]
    for p in outside:
        print(f"E-scope: {p} changed, but step {args.step} does not declare it; "
              "revert it, or add it to the step's Files with a reason")
    print(f"scope-check: step {args.step}, {len(paths)} changed files, {len(outside)} outside its Files")
    return 1 if outside else 0


if __name__ == "__main__":
    sys.exit(main())
