#!/usr/bin/env python3
"""findings-check — the audit-and-fix loop of Phase 5 converges, or it stops.

Phase 5 audits a change, the agent fixes the findings, and the audit runs again.
Each round should find less. When a later round still finds new serious
problems, or reopens one that was fixed, more rounds will not converge: the
fixes create defects, or the specification lets the defects through. The
cause is then in the spec or in the harness, not in the agent, and the
engineer must decide how to route it. This check reads the findings ledger
and stops the loop at that point.

Usage:
    findings-check.py LEDGER [--max-rounds N]   N defaults to 3

The ledger is a Markdown file in kb/reports/ with one table:

    | ID | Round | Severity | Finding | Status | Reopened | Evidence |

    Round      the audit round that found it (1, 2, ...)
    Severity   high, medium or low
    Status     open, fixed or rejected
    Reopened   the round that found it again after a fix, or empty
    Evidence   for fixed: the test or commit; for rejected: the reason

A line `Escalated: round N, <decision>` records the engineer's decision to go on
after round N (`forebrief:<card-id>`, or the date and the engineer's words).

The current round is the largest Round or Reopened value. A round from 2 on
"strikes" when it finds a new high finding or reopens a high one.

Exit code: 0 = the loop may continue or stop, 1 = errors, 2 = unreadable ledger.

Checks:
    E-streak    the current round and the one before it both strike: stop
                fixing, route the failure with the engineer, and record the
                decision as an Escalated line
    E-cap       the current round is past --max-rounds and a high finding is
                still open
    E-evidence  a fixed finding without its test or commit, or a rejected one
                without its reason
    E-shape     an unknown severity or status, or a round that is not a number

An Escalated line for round N lifts E-streak and E-cap for rounds up to N.

What this does NOT check: that the audit found every problem, that a severity
is honest, or that a fix is right. The adversarial verification does that.
"""

import argparse
from pathlib import Path
import re
import sys

SEVERITIES = {"high", "medium", "low"}
STATUSES = {"open", "fixed", "rejected"}
ESCALATED_RE = re.compile(r"^\s*Escalated:\s*round\s+(\d+)\s*,\s*(\S.*)$", re.IGNORECASE | re.MULTILINE)


def rows(text):
    """Rows of the first table whose header has ID, Round and Status."""
    header, out = None, []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            if header and out:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            names = [c.lower() for c in cells]
            if {"id", "round", "status"} <= set(names):
                header = names
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        out.append(dict(zip(header, cells)))
    return out


def number(text):
    text = text.strip()
    return int(text) if text.isdigit() else None


def check(text, max_rounds):
    errors, table = [], rows(text)
    strikes, rounds = set(), [0]
    for r in table:
        fid = r.get("id", "?")
        found, reopened = number(r.get("round", "")), number(r.get("reopened", ""))
        severity, status = r.get("severity", "").lower(), r.get("status", "").lower()
        if found is None or (r.get("reopened", "").strip() and reopened is None):
            errors.append(f"E-shape: {fid}: Round and Reopened must be round numbers")
            continue
        if severity not in SEVERITIES:
            errors.append(f"E-shape: {fid}: severity `{severity}`; expected high, medium or low")
        if status not in STATUSES:
            errors.append(f"E-shape: {fid}: status `{status}`; expected open, fixed or rejected")
        if status in ("fixed", "rejected") and not r.get("evidence", "").strip():
            needs = "the test or commit that fixed it" if status == "fixed" else "the reason"
            errors.append(f"E-evidence: {fid} is {status} without {needs}")
        rounds += [found] + ([reopened] if reopened else [])
        if severity == "high":
            strikes.update(n for n in (found, reopened) if n and n >= 2)
    current = max(rounds)
    escalated = max((int(m.group(1)) for m in ESCALATED_RE.finditer(text)), default=0)
    if current > escalated and current in strikes and current - 1 in strikes:
        errors.append(f"E-streak: rounds {current - 1} and {current} both found new or reopened high "
                      "findings; stop fixing, route the failure (agent, specification or harness) with "
                      f"the engineer, and record `Escalated: round {current}, <decision>`")
    still_open = [r.get("id", "?") for r in table
                  if r.get("severity", "").lower() == "high" and r.get("status", "").lower() == "open"]
    if current > max_rounds and current > escalated and still_open:
        errors.append(f"E-cap: round {current} is past the cap of {max_rounds} with high findings open "
                      f"({', '.join(still_open)}); escalate to the engineer")
    return errors, len(table), current


def main():
    ap = argparse.ArgumentParser(description="Stop an audit-and-fix loop that does not converge.")
    ap.add_argument("ledger")
    ap.add_argument("--max-rounds", type=int, default=3)
    args = ap.parse_args()
    try:
        text = Path(args.ledger).read_text(encoding="utf-8")
    except OSError as error:
        print(f"findings-check: cannot read {args.ledger}: {error}")
        return 2
    errors, n, current = check(text, args.max_rounds)
    for e in errors:
        print(e)
    print(f"findings-check: {n} findings, round {current}, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
