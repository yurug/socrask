#!/usr/bin/env python3
"""arch-check — keep asking whether the structure still fits the system.

Agents optimize locally: each slice adds code where it is easiest, and the
structure erodes without anyone deciding it. This check computes erosion
signals from Git history against the declared component map, and requires an
architecture review, with the engineer, when one is due.

Usage:
    arch-check.py [--root .] [--max-commits 300] [--report]

Inputs (paths from the repository root):
    kb/architecture/overview.md   table | Component | Paths | Depends on | ...
                                  (Paths: backticked; Depends on: names or -)
    kb/architecture/drivers.md    table | Driver | Source | Served by |
    kb/architecture/reviews/<YYYY-MM-DD>-<slug>.md   review records with lines
        Covers: <commit>          the HEAD the review judged
        Outcome: keep | restructure
        ADR: <path>               required when the outcome is restructure
        Engineer: forebrief:<card-id>
    kb/work/ledger.json           a roadmap milestone whose tasks are all closed
                                  names its `architecture_review` file

Signals, over commits after the latest review's Covers commit:
    coupling  two components without a declared dependency change together in
              at least 5 commits and 30% of the smaller one's commits
    scatter   at least 3 commits each touch 4 or more components
    hotspots  the components with the most commits (reported, no trigger)
    unmapped  changed files that belong to no component (warning)

Exit code: 0 = clean (warnings allowed), 1 = errors.

Checks (E = error, W = warning):
    E-map        no component table, a component without paths, or a dependency
                 on an unknown component
    E-drivers    no drivers table, or a driver whose "Served by" is empty
    E-review     a review record without Covers, Outcome, Engineer evidence, or
                 with a restructure outcome whose ADR does not exist
    E-due        a coupling or scatter signal since the latest review, or a
                 completed milestone without an existing architecture_review
    W-unmapped   changed files outside every component

What this does NOT check: whether the structure is right. The signals point at
symptoms; the review, with the engineer, judges. A Full-tier change also needs
a review, but nothing here can detect the tier; the procedure asks for it.
"""
import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import re
import subprocess
import sys

PATH_RE = re.compile(r"`([^`]+)`")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table(text, header):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and [c.lower() for c in cells(line)][:len(header)] == header:
            return [cells(r) + [""] * len(header) for r in lines[i + 2:] if r.lstrip().startswith("|")]
    return None


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout


def owner_of(path, components):
    best = None
    for name, paths in components.items():
        for p in paths:
            if path == p or path.startswith(p.rstrip("/") + "/"):
                if best is None or len(p) > best[1]:
                    best = (name, len(p))
    return best[0] if best else None


def reviews(root, errors):
    out = []
    for f in sorted((root / "kb/architecture/reviews").glob("*.md")):
        if f.name == "INDEX.md" or f.name.startswith("_"):
            continue
        text = f.read_text(encoding="utf-8")
        field = {k.lower(): v.strip() for k, v in re.findall(r"^(\w+):\s*(.+)$", text, re.MULTILINE)}
        rel = f.relative_to(root)
        if not field.get("covers"):
            errors.append(f"E-review: {rel} has no Covers: <commit>")
        if field.get("outcome") not in ("keep", "restructure"):
            errors.append(f"E-review: {rel} needs Outcome: keep or restructure")
        elif field["outcome"] == "restructure" and not (root / field.get("adr", "").strip("`")).is_file():
            errors.append(f"E-review: {rel} restructures without an existing ADR: <path>")
        if not re.match(r"^forebrief:\S+$", field.get("engineer", "")):
            errors.append(f"E-review: {rel} needs Engineer: forebrief:<card-id>")
        out.append((f.name[:10], field.get("covers"), rel))
    return out


def main():
    ap = argparse.ArgumentParser(description="Architecture erosion signals and review gate.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--max-commits", type=int, default=300)
    ap.add_argument("--report", action="store_true", help="print signals and hotspots")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    errors, warnings = [], []

    overview = root / "kb/architecture/overview.md"
    rows = table(overview.read_text(encoding="utf-8"), ["component", "paths", "depends on"]) \
        if overview.is_file() else None
    if not rows:
        print("arch-check: E-map: kb/architecture/overview.md has no | Component | Paths | Depends on | table")
        return 1
    components, deps = {}, {}
    for name, paths, depends, *_ in rows:
        components[name] = PATH_RE.findall(paths)
        deps[name] = {d.strip() for d in depends.split(",") if d.strip() not in ("", "-")}
        if not components[name]:
            errors.append(f"E-map: component {name} names no backticked path")
    for name, ds in deps.items():
        for d in ds - components.keys():
            errors.append(f"E-map: {name} depends on unknown component {d}")

    drivers = root / "kb/architecture/drivers.md"
    drows = table(drivers.read_text(encoding="utf-8"), ["driver", "source", "served by"]) \
        if drivers.is_file() else None
    if not drows:
        errors.append("E-drivers: kb/architecture/drivers.md has no | Driver | Source | Served by | table")
    for d in drows or []:
        if not d[2]:
            errors.append(f"E-drivers: driver `{d[0]}` says nothing under Served by")

    recs = reviews(root, errors)
    latest = max(recs, default=None)
    since = latest[1] if latest and latest[1] else None
    rev_range = [f"{since}..HEAD"] if since and git(root, "rev-parse", "--verify", "-q", since).strip() else []
    log = git(root, "log", f"--max-count={args.max_commits}", "--name-only", "--format=@@%H", *rev_range)
    commits = [c.split("\n", 1)[1].split() if "\n" in c else [] for c in log.split("@@")[1:]]

    touched, pair, scatter, unmapped = Counter(), Counter(), 0, set()
    for files in commits:
        comps = set()
        for f in files:
            owner = owner_of(f, components)
            if owner:
                comps.add(owner)
            elif not f.startswith(("kb/", ".", "docs/")):
                unmapped.add(f)
        touched.update(comps)
        pair.update(combinations(sorted(comps), 2))
        scatter += len(comps) >= 4
    coupled = [(a, b, n) for (a, b), n in pair.items()
               if b not in deps.get(a, set()) and a not in deps.get(b, set())
               and n >= 5 and n >= 0.3 * min(touched[a], touched[b])]
    window = f"since review {latest[2]}" if latest else "over the whole history"
    for a, b, n in coupled:
        errors.append(f"E-due: {a} and {b} changed together in {n} commits {window} without a "
                      "declared dependency; review the architecture")
    if scatter >= 3:
        errors.append(f"E-due: {scatter} commits {window} each touched 4 or more components; "
                      "review the architecture")
    if unmapped:
        sample = ", ".join(sorted(unmapped)[:5])
        warnings.append(f"W-unmapped: {len(unmapped)} changed files belong to no component ({sample})")

    ledger = root / "kb/work/ledger.json"
    if ledger.is_file():
        data = json.loads(ledger.read_text(encoding="utf-8"))
        status = {t["id"]: t.get("status") for t in data.get("tasks", [])}
        for p in data.get("projects", []):
            for m in p.get("roadmap", {}).get("milestones", []):
                tasks = m.get("tasks", [])
                if tasks and all(status.get(t) == "closed" for t in tasks):
                    ref = m.get("architecture_review", "")
                    if not (ref and (root / ref).is_file()):
                        errors.append(f"E-due: milestone {p['id']}/{m.get('id')} is complete without "
                                      "an existing architecture_review")

    if args.report:
        print(f"commits {window}: {len(commits)}; hotspots: "
              + ", ".join(f"{c} ({n})" for c, n in touched.most_common(3)))
    for m in errors + warnings:
        print(m)
    print(f"arch-check: {len(components)} components, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
