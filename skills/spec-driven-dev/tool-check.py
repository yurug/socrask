#!/usr/bin/env python3
"""tool-check — every project tool is in the catalog, and every tool has a test.

Agents repeat by hand what a script would do the same way each time, often
because they do not know the script exists. The catalog in
`kb/conventions/tools.md` tells them, and this check keeps it complete: a
script in a tool directory that the catalog does not list fails the build, as
does a catalog row that points nowhere or names no test.

Usage:
    tool-check.py [CATALOG] [--dir DIR]...   CATALOG defaults to kb/conventions/tools.md,
                                             DIR to tools (repeat for scripts/, bin/ ...)

Run it from the project root: catalog paths are relative to it.
Exit code: 0 = clean, 1 = errors.

The catalog's first table whose header has Tool and Kind columns is read; the
other columns are Does and Test. A Tool cell names the tool in backticks, as a
path (`tools/gen-api.py --check`) or as a command (`dune build @fmt`). Only a
first word that contains `/` is taken as a path.

Checks:
    E-catalog   the catalog is missing while a tool directory holds project scripts
    E-unlisted  a script in a tool directory has no catalog row
    E-missing   a row names a path that does not exist
    E-kind      a row's kind is not check, transform, generate, query or run
    E-test      a row's Test names no existing path and is not `none: <reason>`
                (a reason of three words or more)

A script is a file with a script extension or the executable bit. Tests
(`test-*`, `test_*`, `*_test.*`, `*.test.*`), fixtures and the kit files listed
in `tools/socrask.json` are not project tools and need no row.

What this does NOT check: that a tool is deterministic or idempotent, that its
test covers its contract, or that an agent used the tool instead of editing by
hand. The review and the milestone retrospective cover those.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys

KINDS = {"check", "transform", "generate", "query", "run"}
SCRIPT_EXT = {".py", ".sh", ".bash", ".mjs", ".js", ".cjs", ".ts", ".rb", ".pl", ".ml"}
SKIP_DIRS = {"fixtures", "__pycache__", "node_modules", "_build", ".venv"}
TEST_RE = re.compile(r"^test[-_]|[-_.]test\.[^.]+$")
CODE_RE = re.compile(r"`([^`]+)`")
NONE_RE = re.compile(r"^none:\s*(\S+\s+){2,}\S*")


def catalog_rows(path):
    """Rows of the first table whose header has Tool and Kind, as
    {lower-cased column: cell}. Columns are found by name, so their order is free."""
    header, rows = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            if header and rows:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            names = [c.lower() for c in cells]
            if "tool" in names and "kind" in names:
                header = names
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue  # the separator row
        rows.append(dict(zip(header, cells)))
    return rows


def kit_files():
    """The kit's vendored files: they are documented by the kit, not the project."""
    manifest = Path("tools/socrask.json")
    if not manifest.is_file():
        return set()
    return {os.path.normpath(p) for p in json.loads(manifest.read_text(encoding="utf-8")).get("files", {})}


def project_scripts(dirs):
    kit = kit_files()
    for d in dirs:
        for path in sorted(Path(d).rglob("*")) if Path(d).is_dir() else []:
            if not path.is_file() or SKIP_DIRS.intersection(path.parts) or TEST_RE.search(path.name):
                continue
            if path.suffix in SCRIPT_EXT or os.access(path, os.X_OK):
                if os.path.normpath(path) not in kit:
                    yield os.path.normpath(path)


def tool_paths(cell):
    """The paths a Tool cell names: the first word of each code span, when it has a `/`."""
    words = [span.split()[0] for span in CODE_RE.findall(cell) if span.split()]
    return [os.path.normpath(w) for w in words if "/" in w]


def check(catalog, dirs):
    errors = []
    scripts = list(project_scripts(dirs))
    if not catalog.is_file():
        if scripts:
            errors.append(f"E-catalog: {catalog} is missing, and {len(scripts)} project scripts need a row; "
                          "start it from templates/kb/conventions/tools.md")
        return errors, 0
    rows = catalog_rows(catalog)
    listed = set()
    for row in rows:
        name = row.get("tool", "")
        paths = tool_paths(name)
        listed.update(paths)
        for p in paths:
            if not Path(p).exists():
                errors.append(f"E-missing: {catalog}: tool {name} names `{p}`, which does not exist")
        kind = row.get("kind", "").strip("` ").lower()
        if kind not in KINDS:
            errors.append(f"E-kind: {catalog}: tool {name} has kind `{kind}`; expected one of "
                          + ", ".join(sorted(KINDS)))
        test = row.get("test", "").strip()
        tests = [s.split()[0] for s in CODE_RE.findall(test) if s.split()]
        if NONE_RE.match(test.strip("`")):
            continue
        if not tests:
            errors.append(f"E-test: {catalog}: tool {name} names no test; "
                          "write one, or say `none: <reason>`")
        for t in tests:
            if not Path(t).exists():
                errors.append(f"E-test: {catalog}: tool {name} names test `{t}`, which does not exist")
    for s in scripts:
        if s not in listed:
            errors.append(f"E-unlisted: {s} is a project script without a row in {catalog}; "
                          "add one, or delete the script")
    return errors, len(rows)


def main():
    parser = argparse.ArgumentParser(description="Check the project's tool catalog.")
    parser.add_argument("catalog", nargs="?", default="kb/conventions/tools.md")
    parser.add_argument("--dir", action="append", dest="dirs", help="tool directory (default: tools)")
    args = parser.parse_args()
    errors, n = check(Path(args.catalog), args.dirs or ["tools"])
    for e in errors:
        print(e)
    print(f"tool-check: {n} tools in the catalog, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
