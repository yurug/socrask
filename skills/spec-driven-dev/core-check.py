#!/usr/bin/env python3
"""core-check — keep each de Bruijn kernel small, specified and present.

A critical output (high cost of error) passes through a small checker before
it takes effect. The checker is worth trusting only while it stays small and
its specification exists. `kb/architecture/critical-core.md` declares each
kernel; this script holds the declaration to the repository. A kernel can
also claim a formal assurance level; the claim holds only while nothing it
covers has changed since the proof.

Usage:
    core-check.py [DECLARATION] [--report] [--window N]

    DECLARATION   defaults to ./kb/architecture/critical-core.md
    --report      also list, per kernel, its level and the commits that touched
                  it in the last N commits; an A0 kernel untouched over a full
                  window is a candidate for a proof (no failure)
    --window N    the stability window for --report (default 50 commits)

Declaration shape: one markdown table with columns
Output | Checker | Budget | Spec, optionally followed by Assurance | Proof |
Proved at. Checker lists backticked file paths; Budget is the maximum total
line count of those files; Spec is the `kb/models/<file>.md` path of the
kernel's specification. Assurance is A0 (tests, the default), A1 (the model is
proved) or A2 (the checker is extracted from the proof). Proof lists the
backticked proof files; Proved at is the commit at which the proof was
checked. Paths are written from the repository root.

Exit code: 0 = clean, 1 = errors.

Checks:
    E-missing   the declaration file does not exist
    E-table     no table with Output/Checker/Budget/Spec columns, or no row
    E-file      a checker file does not exist
    E-budget    Budget is not a positive integer, or the checker files exceed it
    E-spec      Spec names no existing `kb/models/...md` file
    E-assurance Assurance is not A0, A1 or A2
    E-proof     an A1 or A2 kernel names no existing proof file
    E-proved-at an A1 or A2 kernel names no commit that exists
    E-stale     a checker, spec or proof file changed since Proved at
    E-admit     a Rocq or Lean proof file admits a goal, or declares an axiom
                the model's `Trusted:` line does not name

What this does NOT check: that the kernel does not depend on its producer, that
the list of critical outputs is complete, that the checker is correct, or that
the proof builds. The proof build (and `Print Assumptions` in Rocq) belongs in
CI; the admit scan is textual and covers `.v` and `.lean` files only.
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys

COLUMNS = ["output", "checker", "budget", "spec"]
LEVELS = ("A0", "A1", "A2")
PATH_RE = re.compile(r"`([^`]+)`")
ADMIT = {".v": re.compile(r"\b(Admitted|admit)\b"), ".lean": re.compile(r"\b(sorry|admit)\b")}
AXIOM = {".v": re.compile(r"\b(?:Axioms?|Parameters?|Conjecture)\s+([\w']+)"),
         ".lean": re.compile(r"\baxiom\s+([\w'.]+)")}


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_rows(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        header = [c.lower() for c in cells(line)]
        if line.lstrip().startswith("|") and header[:4] == COLUMNS:
            rows = []
            for row in lines[i + 2:]:
                if not row.lstrip().startswith("|"):
                    break
                rows.append(dict(zip(header, cells(row) + [""] * len(header))))
            return rows
    return None


def kernel_files(declaration):
    """Checker paths declared in DECLARATION, for other tools (plan-check)."""
    rows = parse_rows(declaration.read_text(encoding="utf-8")) if declaration.is_file() else None
    return {p for row in rows or [] for p in PATH_RE.findall(row["checker"])}


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return result.stdout.split() if result.returncode == 0 else None


def strip_comments(text, suffix):
    """Drop Rocq `(* *)` or Lean `/- -/` and `--` comments, nesting included."""
    open_, close = ("(*", "*)") if suffix == ".v" else ("/-", "-/")
    out, depth, i = [], 0, 0
    while i < len(text):
        if text.startswith(open_, i):
            depth, i = depth + 1, i + 2
        elif depth and text.startswith(close, i):
            depth, i = depth - 1, i + 2
        elif not depth and suffix == ".lean" and text.startswith("--", i):
            i = text.find("\n", i) if "\n" in text[i:] else len(text)
        else:
            if not depth:
                out.append(text[i])
            i += 1
    return "".join(out)


def trusted_line(spec_path):
    if not spec_path.is_file():
        return ""
    return " ".join(l for l in spec_path.read_text(encoding="utf-8").splitlines()
                    if l.strip().startswith("Trusted:"))


def check_assurance(root, name, row, files, spec_file, errors):
    level = row.get("assurance", "").strip("` ") or "A0"
    if level not in LEVELS:
        errors.append(f"E-assurance: {name} assurance `{level}` is not A0, A1 or A2")
        return level
    if level == "A0":
        return level
    proofs = PATH_RE.findall(row.get("proof", ""))
    if not proofs:
        errors.append(f"E-proof: {name} is {level} but names no proof file in backticks")
    trusted = trusted_line(root / spec_file)
    for p in proofs:
        path = root / p
        if not path.is_file():
            errors.append(f"E-proof: {name} proof `{p}` does not exist")
            continue
        if path.suffix not in ADMIT:
            continue
        text = strip_comments(path.read_text(encoding="utf-8", errors="replace"), path.suffix)
        if ADMIT[path.suffix].search(text):
            errors.append(f"E-admit: {name} proof `{p}` admits a goal")
        for axiom in AXIOM[path.suffix].findall(text):
            if not re.search(rf"\b{re.escape(axiom)}\b", trusted):
                errors.append(f"E-admit: {name} proof `{p}` declares axiom `{axiom}`, "
                              f"absent from the Trusted: line of `{spec_file}`")
    commit = row.get("proved at", "").strip("` ")
    if not commit or git(root, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}") is None:
        errors.append(f"E-proved-at: {name} is {level} but `{commit or '-'}` is not a commit")
        return level
    changed = git(root, "diff", "--name-only", commit, "--", *files, spec_file, *proofs)
    if changed:
        errors.append(f"E-stale: {name} is {level} but changed since {commit}: "
                      f"{', '.join(changed)}; prove it again or declare A0")
    return level


def report(root, name, level, paths, window):
    recent = git(root, "rev-list", f"--max-count={window}", "HEAD") or []
    touched = set(git(root, "rev-list", "HEAD", "--", *paths) or []) & set(recent)
    if level != "A0":
        verdict = "proved"
    elif len(recent) < window:
        verdict = f"history shorter than the {window}-commit window"
    elif touched:
        verdict = "moving"
    else:
        verdict = "candidate for A1 or A2"
    return f"{name}: {level}, {len(touched)} of the last {len(recent)} commits touch it: {verdict}"


def main():
    parser = argparse.ArgumentParser(description="Check declared de Bruijn kernels.")
    parser.add_argument("declaration", nargs="?", default="kb/architecture/critical-core.md")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--window", type=int, default=50)
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
    errors, reports = [], []
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
        spec_file = spec[0].split("#")[0]
        if not (spec[0].startswith("kb/models/") and spec_file.endswith(".md")
                and (root / spec_file).is_file()):
            errors.append(f"E-spec: {name} spec `{row['spec']}` is not an existing kb/models/ file")
        level = check_assurance(root, name, row, files, spec_file, errors)
        if args.report:
            paths = files + [spec_file] + PATH_RE.findall(row.get("proof", ""))
            reports.append(report(root, name, level, paths, args.window))
    for r in reports:
        print(f"{decl}: report: {r}")
    for e in errors:
        print(f"{decl}: {e}")
    print(f"{decl}: {len(rows)} kernels, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
