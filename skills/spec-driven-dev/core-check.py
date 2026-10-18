#!/usr/bin/env python3
"""core-check — keep each de Bruijn kernel small, specified and present.

A critical output (high cost of error) passes through a small checker before
it takes effect. The checker is worth trusting only while it stays small and
its specification exists. `kb/architecture/critical-core.md` declares each
kernel; this script holds the declaration to the repository.

Usage:
    core-check.py [DECLARATION]

    DECLARATION   defaults to ./kb/architecture/critical-core.md

Declaration shape: one markdown table with columns
Output | Checker | Budget | Spec. Checker lists backticked file paths; Budget
is the maximum total line count of those files; Spec is the
`kb/models/<file>.md` path of the kernel's specification. Paths are written
from the repository root.

Exit code: 0 = clean, 1 = errors.

Checks:
    E-missing   the declaration file does not exist
    E-table     no table with Output/Checker/Budget/Spec columns, or no row
    E-file      a checker file does not exist
    E-budget    Budget is not a positive integer, or the checker files exceed it
    E-spec      Spec names no existing `kb/models/...md` file

What this does NOT check: that the kernel does not depend on its producer, that
the list of critical outputs is complete, or that the checker is correct.
"""

import argparse
from pathlib import Path
import re
import sys

COLUMNS = ["output", "checker", "budget", "spec"]
PATH_RE = re.compile(r"`([^`]+)`")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_rows(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and [c.lower() for c in cells(line)][:4] == COLUMNS:
            rows = []
            for row in lines[i + 2:]:
                if not row.lstrip().startswith("|"):
                    break
                rows.append(dict(zip(COLUMNS, cells(row) + [""] * 4)))
            return rows
    return None


def kernel_files(declaration):
    """Checker paths declared in DECLARATION, for other tools (plan-check)."""
    rows = parse_rows(declaration.read_text(encoding="utf-8")) if declaration.is_file() else None
    return {p for row in rows or [] for p in PATH_RE.findall(row["checker"])}


def main():
    parser = argparse.ArgumentParser(description="Check declared de Bruijn kernels.")
    parser.add_argument("declaration", nargs="?", default="kb/architecture/critical-core.md")
    args = parser.parse_args()
    decl = Path(args.declaration)
    if not decl.is_file():
        print(f"{decl}: E-missing: no critical-core declaration")
        return 1
    rows = parse_rows(decl.read_text(encoding="utf-8"))
    if not rows:
        print(f"{decl}: E-table: no row in a table with columns Output | Checker | Budget | Spec")
        return 1
    # The declaration normally sits in kb/architecture/; paths are written from the repo root.
    root = next((r for r in (decl.parent.parent.parent, Path(".")) if (r / "kb").is_dir()), Path("."))
    errors = []
    for row in rows:
        name = row["output"] or "?"
        files = PATH_RE.findall(row["checker"])
        if not files:
            errors.append(f"E-file: {name} names no checker file in backticks")
        total = 0
        for f in files:
            path = root / f
            if path.is_file():
                total += len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            else:
                errors.append(f"E-file: {name} checker `{f}` does not exist")
        budget = row["budget"].strip("` ")
        if not budget.isdigit() or int(budget) <= 0:
            errors.append(f"E-budget: {name} budget `{row['budget']}` is not a positive line count")
        elif total > int(budget):
            errors.append(f"E-budget: {name} checker is {total} lines, over its budget of {budget}")
        else:
            print(f"{decl}: {name}: {total}/{budget} lines")
        spec = PATH_RE.findall(row["spec"]) or [row["spec"]]
        if not (spec[0].startswith("kb/models/") and spec[0].split("#")[0].endswith(".md")
                and (root / spec[0].split("#")[0]).is_file()):
            errors.append(f"E-spec: {name} spec `{row['spec']}` is not an existing kb/models/ file")
    for e in errors:
        print(f"{decl}: {e}")
    print(f"{decl}: {len(rows)} kernels, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
