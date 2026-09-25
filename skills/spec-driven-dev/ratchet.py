#!/usr/bin/env python3
"""What passed stays passed. See docs/ratchet.md for the result contract.

Use --from-results FILE for complete, structured runner results, or --passing
IDS for a trusted manual adapter. Raw console logs are not evidence of passing.
Exit codes: 0 held/advanced, 1 failed check/regression, 2 invalid input or I/O.
"""

import argparse
import fcntl
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager


def claim_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:P|NF|T)-?\d+", value):
        raise ValueError(f"invalid obligation ID: {value!r}")
    return value.replace("-", "")


def sort_key(claim):
    m = re.fullmatch(r"([A-Z]+)(\d+)", claim)
    return m.group(1), int(m.group(2)), claim


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        return {"passing": [], "retired": {}}
    if not isinstance(state, dict) or not isinstance(state.get("passing"), list) or not isinstance(state.get("retired"), dict):
        raise ValueError("invalid ratchet state: expected passing list and retired object")
    state["passing"] = [claim_id(c) for c in state["passing"]]
    for c, reason in state["retired"].items():
        claim_id(c)
        if not isinstance(reason, str):
            raise ValueError("invalid retirement reason in state")
    return state


def save(path, state):
    """Publish complete JSON atomically; never truncate the existing state."""
    state["passing"] = sorted(set(state["passing"]), key=sort_key)
    fd, temporary = tempfile.mkstemp(prefix=".ratchet-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked_state(path):
    # Lock a stable sidecar inode: locking the state itself breaks on replace.
    # Keep the sidecar after release so waiting processes retain the same lock.
    with open(path + ".lock", "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield load(path)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def results(path):
    with open(path, encoding="utf-8") as f:
        report = json.load(f)
    if (not isinstance(report, dict) or type(report.get("version")) is not int
            or report["version"] != 1 or report.get("complete") is not True
            or not isinstance(report.get("tests"), list) or not report["tests"]):
        raise ValueError("results require version: 1, complete: true, and a nonempty tests array")
    statuses = {}
    test_ids = set()
    for test in report["tests"]:
        if not isinstance(test, dict):
            raise ValueError("each test must be an object")
        test_id = test.get("id")
        if not isinstance(test_id, str) or not test_id.strip() or test_id in test_ids:
            raise ValueError("each test needs a unique nonempty id")
        test_ids.add(test_id)
        claim = claim_id(test.get("obligation"))
        status = test.get("status")
        if not isinstance(status, str) or status not in {"passed", "failed", "skipped"}:
            raise ValueError("each test status must be passed, failed, or skipped")
        statuses.setdefault(claim, set()).add(status)
    passing = {c for c, s in statuses.items() if s == {"passed"}}
    failed = {c for c, s in statuses.items() if "failed" in s}
    return passing, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-results", metavar="FILE", help="complete structured JSON results")
    src.add_argument("--from-log", metavar="FILE", help="unsupported: migrate to --from-results")
    src.add_argument("--passing", metavar="IDS", help="trusted manual adapter: comma-separated passing IDs")
    src.add_argument("--retire", metavar="ID", help="deliberately drop an obligation (needs --reason)")
    ap.add_argument("--state", default=".ratchet.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reason", default="")
    ap.add_argument("--pattern", help="unsupported legacy log extraction option")
    args = ap.parse_args()
    if args.from_log is not None or args.pattern is not None:
        ap.error("raw logs cannot prove success; migrate to --from-results FILE (see docs/ratchet.md), or use --passing IDS only with a trusted adapter")
    try:
        if args.retire is not None:
            claim = claim_id(args.retire)
            if len(args.reason.strip()) < 20:
                raise ValueError("--retire needs --reason (>= 20 chars)")
        else:
            if args.reason:
                raise ValueError("--reason requires --retire")
            if args.from_results is not None:
                now, failed = results(args.from_results)
                if failed:
                    print("ratchet: FAILED " + ", ".join(sorted(failed, key=sort_key)))
                    return 1
                if not now:
                    print("ratchet: no obligation has complete passing evidence")
                    return 1
            else:
                if not args.passing.strip():
                    raise ValueError("--passing requires at least one obligation ID")
                now = {claim_id(c.strip()) for c in args.passing.split(",")}
        state_path = os.path.realpath(args.state)
        with locked_state(state_path) as state:
            if args.retire is not None:
                state["passing"] = [c for c in state["passing"] if c != claim]
                state["retired"][claim] = args.reason.strip()
                if not args.dry_run:
                    save(state_path, state)
                print(f"ratchet: retired {claim} -- {args.reason.strip()}")
                return 0
            before = set(state["passing"])
            regressed = sorted(before - now, key=sort_key)
            gained = sorted(now - before, key=sort_key)
            if regressed:
                for claim in regressed:
                    print(f"  REGRESSED {claim}")
                print("Fix the regression, or use --retire ID --reason '<why it is gone>'.")
                return 1
            state["passing"] = sorted(before | now, key=sort_key)
            if not args.dry_run:
                save(state_path, state)
            if gained:
                print(f"ratchet: advanced to {len(state['passing'])} (+{len(gained)}: {', '.join(gained)})")
            else:
                print(f"ratchet: held at {len(state['passing'])}")
            return 0
    except (OSError, ValueError, UnicodeError) as e:
        print(f"ratchet: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
