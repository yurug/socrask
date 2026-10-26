#!/usr/bin/env python3
"""case-leak-check — production code never names an acceptance case.

An agent that cannot make an acceptance case pass with the general rule is
tempted to add a special case for it: an `if` on the case's name, a branch on
its fixture, a constant copied from its data. The case then passes and proves
nothing. This check refuses production code that names a declared case.

Usage:
    case-leak-check.py [CONFIG]

    CONFIG   defaults to ./kb/work/case-leak.json

Config (paths from the repository root):
    {"version": 1,
     "sources": ["src/"],                    production code, files or directories
     "cases":   ["tests/acceptance/*.json"], case files; each file stem is a marker
     "markers": ["CASE-042"]}                more markers: case IDs, fixture names

Exit code: 0 = clean, 1 = errors.

Checks:
    E-config  the config is missing, malformed, or declares no source or marker
    E-leak    a production file names a marker

What this does NOT check: a special case that names nothing, such as a magic
value copied from a case's data, or a branch on a shape only that case has.
The review asks that question; this check catches the common form.
"""

import argparse
import json
from pathlib import Path
import re
import sys


def load(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("expected a version-1 JSON object")
    for key in ("sources", "cases", "markers"):
        if not all(isinstance(v, str) and v for v in config.get(key, [])):
            raise ValueError(f"`{key}` must be a list of nonempty strings")
    return config


def files_under(root, entries):
    for entry in entries:
        path = root / entry
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from (p for p in sorted(path.rglob("*")) if p.is_file())


def text_of(path):
    data = path.read_bytes()
    return None if b"\0" in data[:8192] else data.decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="Refuse production code that names an acceptance case.")
    parser.add_argument("config", nargs="?", default="kb/work/case-leak.json")
    args = parser.parse_args()
    path = Path(args.config)
    try:
        config = load(path)
    except (OSError, ValueError) as e:
        print(f"{path}: E-config: {e}")
        return 1
    root = next((r for r in (path.parent.parent.parent, Path(".")) if (r / "kb").is_dir()), Path("."))
    case_files = {p.resolve() for g in config.get("cases", []) for p in root.glob(g) if p.is_file()}
    markers = set(config.get("markers", [])) | {p.stem for p in case_files}
    if not config.get("sources") or not markers:
        print(f"{path}: E-config: declare at least one source and one marker or case file")
        return 1
    pattern = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, sorted(markers, key=len, reverse=True)))
                         + r")(?![\w-])")
    errors = scanned = 0
    for f in files_under(root, config["sources"]):
        if f.resolve() in case_files:
            continue
        text = text_of(f)
        if text is None:
            continue
        scanned += 1
        for n, line in enumerate(text.splitlines(), 1):
            for m in pattern.finditer(line):
                print(f"{f.relative_to(root)}:{n}: E-leak: names acceptance case `{m.group(1)}`; "
                      "fix the general rule instead")
                errors += 1
    print(f"case-leak-check: {scanned} files, {len(markers)} markers, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
