#!/usr/bin/env python3
"""Coordinate agents on different machines or under different engineers.

The shared medium is the project's Git remote. Claims live in the ref
`refs/socrask/registry`: each update is a commit holding `registry.json`, with
the previous state as parent. A concurrent update is a non-fast-forward push,
so the remote rejects it and this tool re-reads and retries: the registry is
compare-and-swap without a server. The commit history is the audit log.

Inside one engineer's claim, that engineer's agents on one machine keep using
`agent-work.py` (local worktrees and runs); their local claims stay within the
team claim's paths.

Usage:
    team-work.py status
    team-work.py claim --task T --engineer E --path P... --criteria C [--lease-hours 4]
    team-work.py renew --task T --engineer E [--lease-hours 4]
    team-work.py takeover --task T --engineer E --reason R     (expired lease only)
    team-work.py handoff --task T --engineer E --pr URL [--commit SHA]
    team-work.py close --task T --engineer E --outcome integrated|abandoned --reason R

    --remote         defaults to origin
    --ci-status-cmd  prints success/failure/pending for a commit; `{sha}` is
                     replaced; defaults to the GitHub check runs via `gh`

Rules:
    - claimed paths of two unexpired, unclosed tasks never overlap;
    - a claim records the kit revision; if the project pins one in
      kb/work/kit-revision, a different revision is refused;
    - a handoff cites a pull request and a CI result `success` on the exact commit;
    - `integrated` closure needs the handoff commit merged into the remote's
      default branch;
    - CODEOWNERS entries for claimed paths that name other people are listed as
      `consult`: decisions in those areas go to them.

What this does NOT do: authenticate engineers beyond Git push access, correct
clock skew between machines (leases use UTC timestamps), or replace review.
"""
import argparse
from datetime import datetime, timedelta, timezone
import fnmatch
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

REF = "refs/socrask/registry"
LOCAL = "refs/socrask/registry-remote"
DEFAULT_CI = ("gh api repos/{owner}/{repo}/commits/{sha}/check-runs "
              "--jq '[.check_runs[].conclusion] | if length == 0 then \"pending\" "
              "elif all(. == \"success\" or . == \"skipped\" or . == \"neutral\") then \"success\" "
              "elif any(. == null) then \"pending\" else \"failure\" end'")


def load_local_rules():
    """Path rules shared with agent-work.py, so both tools agree on what a claim covers."""
    spec = importlib.util.spec_from_file_location("agent_work", Path(__file__).with_name("agent-work.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.normalized, module.overlaps


normalized, overlaps = load_local_rules()


def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode:
        raise ValueError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip() if result.returncode == 0 else None


def now():
    return datetime.now(timezone.utc)


def stamp(t):
    return t.isoformat(timespec="seconds")


def fetch(remote):
    """(state, parent sha) of the remote registry; an empty state if it does not exist."""
    if git("fetch", "-q", remote, f"+{REF}:{LOCAL}", check=False) is None:
        return {"version": 1, "tasks": {}}, None
    sha = git("rev-parse", LOCAL)
    return json.loads(git("show", f"{sha}:registry.json")), sha


def publish(remote, state, parent, message):
    blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=json.dumps(
        state, indent=2, sort_keys=True) + "\n", capture_output=True, text=True, check=True).stdout.strip()
    tree = subprocess.run(["git", "mktree"], input=f"100644 blob {blob}\tregistry.json\n",
                          capture_output=True, text=True, check=True).stdout.strip()
    commit = git("commit-tree", tree, *(["-p", parent] if parent else []), "-m", message)
    # A non-fast-forward push is the compare-and-swap failure: someone else moved the ref.
    return git("push", "-q", remote, f"{commit}:{REF}", check=False) is not None


def transact(remote, mutate, message, attempts=5):
    for _ in range(attempts):
        state, parent = fetch(remote)
        result = mutate(state)
        if publish(remote, state, parent, message):
            return result
    raise ValueError("registry kept moving; retry later")


def expired(task, at=None):
    return task["status"] in ("active", "ready") and \
        datetime.fromisoformat(task["lease_until"]) < (at or now())


def live(task):
    return task["status"] in ("active", "ready") and not expired(task)


def kit_revision():
    return git("-C", str(Path(__file__).resolve().parent), "rev-parse", "HEAD", check=False)


def codeowners(paths, engineer):
    """Owners named by CODEOWNERS for these paths, other than the engineer."""
    for candidate in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS", ".gitlab/CODEOWNERS"):
        if Path(candidate).is_file():
            rules = []
            for line in Path(candidate).read_text().splitlines():
                parts = line.split("#", 1)[0].split()
                if len(parts) >= 2:
                    rules.append((parts[0].strip("/"), parts[1:]))
            found = set()
            for p in paths:
                owners = []
                for pattern, who in rules:  # last match wins, as on the forges
                    if pattern == "*" or fnmatch.fnmatch(p, pattern) or overlaps(p, pattern.rstrip("/*")):
                        owners = who
                found.update(o for o in owners if o.lstrip("@") != engineer.lstrip("@"))
            return sorted(found)
    return []


def owned(state, args):
    task = state["tasks"].get(args.task)
    if not task:
        raise ValueError(f"no task {args.task}")
    if task["engineer"] != args.engineer:
        raise ValueError(f"{args.task} belongs to {task['engineer']}")
    return task


def ci_status(cmd, sha):
    out = subprocess.run(cmd.replace("{sha}", sha), shell=True, capture_output=True, text=True)
    return out.stdout.strip().strip('"') or "unknown"


def default_branch(remote):
    head = git("ls-remote", "--symref", remote, "HEAD", check=False) or ""
    for line in head.splitlines():
        if line.startswith("ref:"):
            return line.split()[1].removeprefix("refs/heads/")
    return "main"


def parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--ci-status-cmd", default=DEFAULT_CI)
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    for name in ("claim", "renew", "takeover", "handoff", "close"):
        p = sub.add_parser(name)
        p.add_argument("--task", required=True)
        p.add_argument("--engineer", required=True)
        if name in ("claim", "renew", "takeover"):
            p.add_argument("--lease-hours", type=float, default=4)
        if name == "claim":
            p.add_argument("--path", action="append", required=True)
            p.add_argument("--criteria", required=True)
            p.add_argument("--base", default="HEAD")
        if name in ("takeover", "close"):
            p.add_argument("--reason", required=True)
        if name == "handoff":
            p.add_argument("--pr", required=True)
            p.add_argument("--commit", default="HEAD")
        if name == "close":
            p.add_argument("--outcome", choices=["integrated", "abandoned"], required=True)
    return ap


def main():
    args = parser().parse_args()
    os.chdir(git("rev-parse", "--show-toplevel"))
    agent = f"{os.environ.get('USER', 'agent')}@{socket.gethostname()}"

    if args.action == "status":
        state, _ = fetch(args.remote)
        for t in sorted(state["tasks"].values(), key=lambda t: t["id"]):
            flag = " EXPIRED" if expired(t) else ""
            print(f"{t['id']} [{t['status']}{flag}] {t['engineer']} ({t['agent']}) "
                  f"until {t['lease_until']}: {', '.join(t['paths'])}"
                  + (f"; consult {', '.join(t['consult'])}" if t.get("consult") else ""))
        return 0

    def lease(hours):
        return stamp(now() + timedelta(hours=hours))

    if args.action == "claim":
        paths = sorted({normalized(p) for p in args.path})
        base = git("rev-parse", "--verify", args.base + "^{commit}")
        kit = kit_revision()
        pin = Path("kb/work/kit-revision")
        if pin.is_file() and pin.read_text().strip() != kit:
            raise ValueError(f"kit revision {kit} differs from the project pin {pin.read_text().strip()}; "
                             "update the kit or the pin first")
        consult = codeowners(paths, args.engineer)
        until = lease(args.lease_hours)

        def claim(state):
            if args.task in state["tasks"]:
                raise ValueError(f"task {args.task} already exists; use a new ID")
            for other in state["tasks"].values():
                if live(other) and any(overlaps(a, b) for a in paths for b in other["paths"]):
                    raise ValueError(f"paths overlap {other['id']} held by {other['engineer']}")
            state["tasks"][args.task] = dict(
                id=args.task, engineer=args.engineer, agent=agent, paths=paths, base=base,
                criteria=args.criteria, kit=kit, consult=consult, status="active",
                claimed_at=stamp(now()), lease_until=until, history=[])
        transact(args.remote, claim, f"claim {args.task} by {args.engineer}")
        print(f"claimed {args.task} until {until}"
              + (f"; decisions in these paths go to {', '.join(consult)}" if consult else ""))
        return 0

    if args.action == "renew":
        def renew(state):
            task = owned(state, args)
            if task["status"] not in ("active", "ready"):
                raise ValueError(f"{args.task} is {task['status']}")
            task["lease_until"] = lease(args.lease_hours)
        transact(args.remote, renew, f"renew {args.task}")
        print(f"renewed {args.task}")
        return 0

    if args.action == "takeover":
        if len(args.reason.split()) < 3:
            raise ValueError("a takeover needs a reason")

        def takeover(state):
            task = state["tasks"].get(args.task)
            if not task or not expired(task):
                raise ValueError(f"{args.task} has no expired lease; ask {task and task['engineer']}")
            task["history"].append(dict(at=stamp(now()), event="takeover", previous=task["engineer"],
                                        by=args.engineer, reason=args.reason))
            task.update(engineer=args.engineer, agent=agent, status="active",
                        lease_until=lease(args.lease_hours))
        transact(args.remote, takeover, f"takeover {args.task} by {args.engineer}")
        print(f"took over {args.task}")
        return 0

    if args.action == "handoff":
        sha = git("rev-parse", "--verify", args.commit + "^{commit}")
        status = ci_status(args.ci_status_cmd, sha)
        if status != "success":
            raise ValueError(f"CI on {sha[:12]} is `{status}`; a cross-machine handoff needs `success`")

        def handoff(state):
            task = owned(state, args)
            if not live(task):
                raise ValueError(f"{args.task} is not active with a valid lease")
            task.update(status="ready", head=sha, pr=args.pr, ci="success", ready_at=stamp(now()))
        transact(args.remote, handoff, f"handoff {args.task}")
        print(f"{args.task} ready at {sha[:12]} ({args.pr})")
        return 0

    if len(args.reason.split()) < 3:
        raise ValueError("closure needs a reason")
    merged = None
    if args.outcome == "integrated":
        branch = default_branch(args.remote)
        git("fetch", "-q", args.remote, branch)
        # Resolve now: the registry fetch inside the transaction overwrites FETCH_HEAD.
        merged = (f"{args.remote}/{branch}", git("rev-parse", "FETCH_HEAD"))

    def close(state):
        task = owned(state, args)
        if args.outcome == "integrated":
            if task["status"] != "ready":
                raise ValueError("integration needs a handoff first")
            if subprocess.run(["git", "merge-base", "--is-ancestor", task["head"], merged[1]]).returncode:
                raise ValueError(f"handoff commit is not merged into {merged[0]}")
        task.update(status="closed", outcome=args.outcome, closure=args.reason, closed_at=stamp(now()))
    transact(args.remote, close, f"close {args.task} {args.outcome}")
    print(f"closed {args.task} ({args.outcome})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print("team-work: " + str(exc), file=sys.stderr)
        sys.exit(2)
