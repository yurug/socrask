#!/usr/bin/env python3
"""ratchet — what passed stays passed.

A loop that re-runs everything and reports green/red does not climb; it
wanders. What makes it climb is a ratchet: the work splits into obligations
that are checked on their own, an obligation that passed stays passed when its
neighbours move, the checker names WHICH one failed, and a repair cannot
quietly undo the rest. None of that is free -- a test suite passing on one
version says nothing about the next one.

This tool holds the second and fourth properties, which are the ones nothing
else in a normal toolchain holds. The first is the KB's job (properties carry
IDs); the third is the test-naming convention (a test name starts with the
property it verifies), which is what makes the IDs extractable here.

Usage:
    ratchet.py --from-log test-output.txt        # extract IDs, compare, advance
    ratchet.py --passing P1,P3,T7                # or pass them directly
    ratchet.py --from-log out.txt --dry-run      # compare, never write
    ratchet.py --retire T4 --reason "T4 merged into T9 by ADR-011"

    --state FILE     ratchet state (default .ratchet.json at the repo root);
                     COMMIT IT -- an uncommitted high-water mark ratchets
                     nothing, it just remembers your last local run
    --pattern RE     how to find obligation IDs in the log
                     (default: a P/NF/T id at the start of a test name)

Exit code: 0 = held or advanced, 1 = regression (or a drop with no reason),
2 = bad invocation.

What it does NOT do: run your tests, know whether a test is meaningful, or
notice an obligation nobody ever wrote a test for. It only refuses to let the
set of passing obligations shrink in silence. `kb-lint`'s E-unenforced is what
catches the obligation that was never checked at all.
"""

import argparse
import json
import os
import re
import sys

DEFAULT_PATTERN = r"""["'`]\s*((?:P|NF|T)-?\d+)(?=[\s:—–\-"'`])"""


def load(path):
    if not os.path.exists(path):
        return {"passing": [], "retired": {}}
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ratchet: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)
    state.setdefault("passing", [])
    state.setdefault("retired", {})
    return state


def save(path, state):
    state["passing"] = sorted(set(state["passing"]), key=sort_key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def sort_key(claim):
    """P2 before P10: sort on the number, not the string."""
    m = re.match(r"([A-Z]+)-?(\d+)", claim)
    return (m.group(1), int(m.group(2))) if m else (claim, 0)


def extract(text, pattern):
    return {m.group(1).replace("-", "") for m in re.finditer(pattern, text)}


def main():
    ap = argparse.ArgumentParser(description="What passed stays passed.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--from-log", metavar="FILE",
                     help="test output to extract passing obligation IDs from")
    src.add_argument("--passing", metavar="IDS",
                     help="comma-separated obligation IDs that pass now")
    ap.add_argument("--state", default=None)
    ap.add_argument("--pattern", default=DEFAULT_PATTERN)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retire", metavar="ID",
                    help="deliberately drop an obligation (needs --reason)")
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    state_path = args.state or ".ratchet.json"

    # -- Retiring is the escape valve, and it is deliberately loud: an
    #    obligation may legitimately disappear (merged, superseded, scope cut),
    #    but only on the record. That is the difference between retiring an
    #    obligation and a repair quietly undoing it.
    if args.retire:
        if len(args.reason.strip()) < 20:
            print("ratchet: --retire needs --reason (>= 20 chars) -- the reason is "
                  "what a later audit reads instead of guessing", file=sys.stderr)
            return 2
        state = load(state_path)
        claim = args.retire.replace("-", "")
        state["passing"] = [c for c in state["passing"] if c != claim]
        state["retired"][claim] = args.reason.strip()
        if not args.dry_run:
            save(state_path, state)
        print(f"ratchet: retired {claim} -- {args.reason.strip()}")
        return 0

    if args.from_log:
        try:
            with open(args.from_log, encoding="utf-8", errors="replace") as f:
                now = extract(f.read(), args.pattern)
        except OSError as e:
            print(f"ratchet: cannot read {args.from_log}: {e}", file=sys.stderr)
            return 2
    elif args.passing is not None:
        now = {c.strip().replace("-", "") for c in args.passing.split(",") if c.strip()}
    else:
        now = extract(sys.stdin.read(), args.pattern)

    state = load(state_path)
    before = set(state["passing"])
    regressed = sorted(before - now, key=sort_key)
    gained = sorted(now - before, key=sort_key)

    if regressed:
        print(f"ratchet: {len(regressed)} obligation(s) that passed before do not now:")
        for claim in regressed:
            print(f"  REGRESSED {claim}")
        print("Fix the regression, or retire the obligation on the record:")
        print(f"  ratchet.py --retire {regressed[0]} --reason \"<why it is gone>\"")
        return 1

    state["passing"] = sorted(before | now, key=sort_key)
    if not args.dry_run:
        save(state_path, state)
    if gained:
        print(f"ratchet: advanced to {len(state['passing'])} "
              f"(+{len(gained)}: {', '.join(gained)})")
    else:
        print(f"ratchet: held at {len(state['passing'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
