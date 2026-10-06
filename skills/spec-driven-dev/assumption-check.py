#!/usr/bin/env python3
"""assumption-check — the Phase 1 exit gate of spec-driven-dev.

Every choice the agent made that neither the KB nor a human decision settles
is a row in the assumption ledger (default `kb/assumptions.md`). "The user
confirmed there are no ambiguities left" asks the human to notice questions
nobody asked; an empty open column is a claim this script can check.

Usage:
    assumption-check.py [LEDGER] [--exit]

    LEDGER   defaults to ./kb/assumptions.md
    --exit   Phase 1 exit gate: any `open` row fails

Ledger shape: one markdown table with columns ID | Assumption | Status | Basis.
    open      not settled yet; Basis may be empty
    resolved  Basis is `forebrief:<card-id>` or a KB/repo path that exists
              (the file where the decision now lives; `#anchor` allowed)
    accepted  the human accepted the default as is; Basis names who and
              when, e.g. `accepted by yann 2026-10-05`

Exit code: 0 = clean (warnings allowed), 1 = errors.

Checks (E = error, W = warning):
    E-missing   the ledger file does not exist
    E-table     no table with ID/Assumption/Status/Basis columns
    E-dup-id    two rows share an ID
    E-status    status outside open/resolved/accepted
    E-basis     resolved/accepted row whose basis does not hold
    E-open      (--exit only) a row is still open
    W-empty     (--exit only) zero rows: either the KB really settles every
                choice, or nobody wrote the choices down

What this does NOT check: that the ledger is complete. A missing row is
invisible here; the independent question pass in Phase 1 is what finds it.
"""

import argparse
from pathlib import Path
import re
import sys

COLUMNS = ["id", "assumption", "status", "basis"]
STATUSES = {"open", "resolved", "accepted"}
FOREBRIEF_RE = re.compile(r"^forebrief:\S+$")
ACCEPTED_RE = re.compile(r"\bby\s+\S+.*\b\d{4}-\d{2}-\d{2}\b", re.IGNORECASE)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_rows(text):
    """Rows of the first table whose header names the ledger columns, or None."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        header = [c.lower() for c in cells(line)]
        if header[:len(COLUMNS)] != COLUMNS:
            continue
        rows = []
        for row in lines[i + 2:]:
            if not row.lstrip().startswith("|"):
                break
            values = cells(row) + [""] * len(COLUMNS)
            rows.append(dict(zip(COLUMNS, values)))
        return rows
    return None


def basis_holds(status, basis, ledger):
    if status == "accepted":
        return bool(ACCEPTED_RE.search(basis))
    if FOREBRIEF_RE.match(basis):
        return True
    path = basis.strip("`").split("#", 1)[0]
    if not path:
        return False
    # The ledger normally sits in kb/, and bases are written from the repo root.
    roots = (ledger.parent.parent, ledger.parent)
    return any((root / path).is_file() for root in roots)


def main():
    parser = argparse.ArgumentParser(description="Phase 1 exit gate: check the assumption ledger.")
    parser.add_argument("ledger", nargs="?", default="kb/assumptions.md")
    parser.add_argument("--exit", action="store_true",
                        help="Phase 1 exit gate: fail on any open row")
    args = parser.parse_args()
    ledger = Path(args.ledger)

    if not ledger.is_file():
        print(f"{ledger}: E-missing: no assumption ledger; Phase 1 has no exit evidence")
        return 1
    rows = parse_rows(ledger.read_text(encoding="utf-8"))
    if rows is None:
        print(f"{ledger}: E-table: no table with columns ID | Assumption | Status | Basis")
        return 1

    errors, warnings, seen = [], [], set()
    for row in rows:
        rid, status, basis = row["id"], row["status"].lower(), row["basis"]
        if rid in seen:
            errors.append(f"E-dup-id: {rid} appears twice")
        seen.add(rid)
        if status not in STATUSES:
            errors.append(f"E-status: {rid} has status `{row['status']}`, "
                          f"expected one of {sorted(STATUSES)}")
        elif status == "open":
            line = f"{rid} is open: {row['assumption']}"
            if args.exit:
                errors.append(f"E-open: {line}")
            else:
                print(f"{ledger}: {line}")
        elif not basis_holds(status, basis, ledger):
            want = ("`accepted by <who> <YYYY-MM-DD>`" if status == "accepted"
                    else "`forebrief:<card-id>` or an existing path")
            errors.append(f"E-basis: {rid} is {status} but its basis `{basis}` "
                          f"is not {want}")

    if args.exit and not rows:
        warnings.append("W-empty: zero assumptions recorded; confirm the KB really "
                        "settles every choice this change makes")

    for message in errors + warnings:
        print(f"{ledger}: {message}")
    n_open = sum(1 for r in rows if r["status"].lower() == "open")
    print(f"{ledger}: {len(rows)} assumptions, {n_open} open")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
