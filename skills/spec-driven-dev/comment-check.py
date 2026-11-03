#!/usr/bin/env python3
"""comment-check — warn on comments that explain nothing.

The code rules ask each comment to explain: a claim, its reason, its consequence.
Two kinds of comment fail that in a way a script can see. A hollow word
("robust", "properly", "handles edge cases") says that something is good without
saying what. A comment that holds only KB IDs ("enforces P4", "per ADR-007")
sends the reader away from the file. This check finds both, across languages.

Usage:
    comment-check.py [PATH...] [--strict] [--exclude GLOB]...
                                         PATH defaults to the current directory

Exit code: 0 = no error (warnings allowed), 1 = warnings with --strict.

Checks:
    W-hollow   a comment uses a word that praises without saying what:
               robust, properly, appropriately, gracefully,
               seamlessly, as needed, as appropriate, edge case(s), for safety,
               just in case, best practice
    W-id-only  a comment whose only content is KB IDs (P4, NF2, T3, M1, I2,
               R5, ADR-007, kb/ paths) and linking words (enforces, per, see)

Comments are found by their markers: `//`, `#` or `--` at the start of a line,
` // ` after code, and block comments such as `/* */` and `(* *)`. Python
docstrings are not read. A marker inside a string can give a false warning. Suppress one on the same or the previous line with
`comment-check: ok <reason of three words or more>`. Without --strict, many
warnings of one code print as one line; --all lists them.

What this does NOT check: that a comment is true, that a file explains its idea,
or that an explanation is missing. The cold read in Phase 5 checks those
(references/explaining-code.md).
"""

import argparse
import fnmatch
from pathlib import Path
import re
import sys

EXTENSIONS = {".py", ".ml", ".mli", ".mly", ".mll", ".rs", ".ts", ".tsx", ".js", ".jsx",
              ".mjs", ".go", ".java", ".kt", ".scala", ".c", ".h", ".cc", ".cpp", ".hpp",
              ".rb", ".php", ".sh", ".ex", ".exs", ".swift", ".cs", ".hs", ".lua", ".sql",
              ".v", ".lean"}
SKIP_DIRS = {".git", "node_modules", "_build", "_opam", "target", "dist", "build", "vendor",
             ".venv", "venv", "__pycache__", "fixtures"}
HOLLOW_RE = re.compile(
    r"\b(robust(?:ly|ness)?|properly|appropriately|gracefully|seamlessly"
    r"|as needed|as appropriate|edge[- ]cases?|for safety|just in case|best practices?)\b",
    re.IGNORECASE)
ID_RE = re.compile(r"\b(?:NF|[PTMIR])\d+\b|\bADR-\d+\b|\bkb/[\w./#-]+")
FILLER_RE = re.compile(
    r"\b(?:enforces?|implements?|satisfies|keeps?|preserves?|per|see|cf|ref|refs|and|"
    r"property|properties|invariant|rule|step|from|by|for|of|the|with|also)\b|[\s,.;:()\[\]#*/-]",
    re.IGNORECASE)
PATH_RE = re.compile(r"\S*/\S*")  # a path such as kb/properties/edge-cases.md is a name
SUPPRESS_RE = re.compile(r"comment-check:\s*ok\s+(\S+\s+){2,}\S*")
GROUP_AFTER = 3
LINE_MARKERS = {".py": "#", ".sh": "#", ".rb": "#", ".ex": "#", ".exs": "#",
                ".hs": "--", ".lua": "--", ".sql": "--", ".lean": "--"}
BLOCKS = {".ml": ("(*", "*)"), ".mli": ("(*", "*)"), ".mly": ("/*", "*/"), ".mll": ("(*", "*)"),
          ".v": ("(*", "*)"), ".lean": ("/-", "-/"), ".hs": ("{-", "-}")}


def files(paths, exclude):
    for root in map(Path, paths):
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if path.suffix in EXTENSIONS and path.is_file() \
                    and not SKIP_DIRS.intersection(path.parts[:-1]) \
                    and not any(fnmatch.fnmatch(path.name, g) for g in exclude):
                yield path


def comments(path, lines):
    """Yield (line number, comment text). A block comment yields one item per line,
    and a run of line comments yields one item for the whole run, so that a claim
    written over several lines is read as one comment."""
    line_marker = LINE_MARKERS.get(path.suffix, "//")
    # Languages with `#` line comments have no block comment that we read.
    opener, closer = BLOCKS.get(path.suffix, ("/*", "*/") if line_marker != "#" else (None, None))
    run, run_start, depth = [], 0, 0
    for n, line in enumerate(lines, 1):
        text = line.strip()
        if depth:
            end = text.find(closer)
            yield n, text if end < 0 else text[:end]
            depth = 0 if end >= 0 else depth
            continue
        if text.startswith(line_marker):
            if not run:
                run_start = n
            run.append(text[len(line_marker):])
            continue
        if run:
            yield run_start, " ".join(run)
            run = []
        start = line.find(opener) if opener else -1
        if start >= 0:
            body = line[start + len(opener):]
            end = body.find(closer)
            yield n, body if end < 0 else body[:end]
            depth = 1 if end < 0 else 0
        elif line_marker == "//" and " // " in line:
            yield n, line.split(" // ", 1)[1]
    if run:
        yield run_start, " ".join(run)


def findings(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for n, text in comments(path, lines):
        if SUPPRESS_RE.search(text) or (n > 1 and SUPPRESS_RE.search(lines[n - 2])):
            continue
        m = HOLLOW_RE.search(PATH_RE.sub("", text))
        if m:
            yield n, "W-hollow", f"`{m.group(0)}` praises without saying what; name the case, property or failure"
        if ID_RE.search(text) and not FILLER_RE.sub("", ID_RE.sub("", text)):
            yield n, "W-id-only", "the comment holds only KB IDs; write the claim in words, then the ID"


def main():
    ap = argparse.ArgumentParser(description="Warn on comments that explain nothing.")
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--strict", action="store_true", help="exit 1 when there is a warning")
    ap.add_argument("--all", action="store_true", help="print every warning, ungrouped")
    ap.add_argument("--exclude", action="append", default=[], help="file-name glob to skip")
    args = ap.parse_args()
    by_code, scanned = {}, 0
    for path in files(args.paths, args.exclude):
        scanned += 1
        for n, code, msg in findings(path):
            by_code.setdefault(code, []).append(f"{path}:{n}: {code}: {msg}")
    total = 0
    for code, hits in by_code.items():
        total += len(hits)
        if args.all or len(hits) <= GROUP_AFTER:
            print("\n".join(hits))
        else:
            first = ", ".join(h.split(": ", 1)[0] for h in hits[:GROUP_AFTER])
            print(f"{code}: {len(hits)} warnings, first at {first}; --all lists them")
    print(f"comment-check: {scanned} files, {total} warnings")
    return 1 if args.strict and total else 0


if __name__ == "__main__":
    sys.exit(main())
