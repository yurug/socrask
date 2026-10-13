#!/usr/bin/env python3
"""ste-check — the writing standard for human-facing artifacts.

Plans, reports, briefs, decision cards and changelogs are read by people who
did not see the session. The kit adopts the writing rules of ASD-STE100
(Simplified Technical English), not its aerospace dictionary: the project
glossary is the approved-term list. Rules are structural, never a readability
score. The standard is in docs/writing-standard.md.

Usage:
    ste-check.py FILE... [--glossary PATH]

    FILE        markdown or plain text; `-` reads stdin (e.g. a card's text)
    --glossary  defaults to ./kb/GLOSSARY.md when it exists

Exit code: 0 = clean (warnings allowed), 1 = errors.

Checks (E = error, W = warning):
    E-long     a sentence over 25 words, or over 20 in a numbered procedure step
    E-term     a word the glossary rejects (`Not:` list after a term) instead
               of the term itself
    W-hedge    should / may / might: write must for a rule, can for a
               possibility, or state the fact
    W-passive  be + past participle: say who does what (heuristic)

Skipped: frontmatter, headings, code blocks, inline code, tables, URLs, and
words cited as words (in quotes or *emphasis*).

What this does NOT check: that a sentence says one thing, that the reader
can act on it, or that the glossary itself is complete and consistent.
"""

import argparse
from pathlib import Path
import re
import sys

LIMIT, PROCEDURE_LIMIT = 25, 20
HEDGE_RE = re.compile(r"\b(should|may|might)\b", re.IGNORECASE)
PASSIVE_RE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+(?:not\s+)?(\w+(?:ed|en))\b", re.IGNORECASE)
NOT_PARTICIPLE = {"often", "even", "open", "then", "when", "seven", "eleven",
                  "token", "given", "need", "used", "based", "supposed", "allowed"}
NOT_RE = re.compile(r"^\s*[-*]\s+\*\*([^*]+)\*\*.*?\bNot:\s*([^.]+)", re.IGNORECASE)
PROCEDURE_RE = re.compile(r"^\s*\d+[.)]\s")
ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
ABBREV_RE = re.compile(r"\b(e\.g|i\.e|etc|vs|cf)\.", re.IGNORECASE)


def blocks(text):
    """Prose blocks as (first line number, is_procedure, [(line no, text)])."""
    lines = text.splitlines()
    i, out, cur = 0, [], None
    if lines and lines[0].strip() == "---" and "---" in [l.strip() for l in lines[1:]]:
        i = [l.strip() for l in lines].index("---", 1) + 1
    fence = False
    for n in range(i, len(lines)):
        line = lines[n]
        if line.lstrip().startswith(("```", "~~~")):
            fence, cur = not fence, None
            continue
        stripped = line.strip()
        if fence or not stripped or stripped.startswith(("#", "|", ">", "<")):
            cur = None
            continue
        if cur is None or ITEM_RE.match(line):
            cur = (n + 1, bool(PROCEDURE_RE.match(line)), [])
            out.append(cur)
        cur[2].append((n + 1, ITEM_RE.sub("", line, count=1)))
    return out


def clean(text):
    text = re.sub(r"`[^`]*`", "code", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "url", text)
    return ABBREV_RE.sub(lambda m: m.group(1).replace(".", ""), text)


def cited_removed(text):
    """Words cited as words are not used as words."""
    text = re.sub(r"\"[^\"]*\"|“[^”]*”", "", text)
    return re.sub(r"\*[^*]+\*", "", text)


def sentences(block):
    """[(line no, sentence)] for one prose block."""
    out, buf, start = [], [], None
    for lineno, line in block:
        for piece in re.split(r"(?<=[.!?;])\s+", clean(line)):
            if not piece.strip():
                continue
            start = start or lineno
            buf.append(piece)
            if re.search(r"[.!?;:]$", piece):
                out.append((start, " ".join(buf)))
                buf, start = [], None
    if buf:
        out.append((start, " ".join(buf)))
    return out


def glossary_terms(path):
    """{rejected word: canonical term} from `- **Term**: ... Not: a, b.` lines."""
    rejected = {}
    if path and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = NOT_RE.match(line)
            if m:
                for word in m.group(2).split(","):
                    if word.strip():
                        rejected[word.strip().strip("`*").lower()] = m.group(1).strip()
    return rejected


def check(name, text, rejected):
    errors, warnings = [], []
    for _, procedure, block in blocks(text):
        limit = PROCEDURE_LIMIT if procedure else LIMIT
        for lineno, s in sentences(block):
            where = f"{name}:{lineno}"
            words = re.findall(r"[\w'’-]+", s)
            if len(words) > limit:
                errors.append(f"{where}: E-long: {len(words)} words (limit {limit}): "
                              f"\"{' '.join(words[:8])} ...\"")
            used = cited_removed(s)
            for bad, term in rejected.items():
                if re.search(rf"\b{re.escape(bad)}(?:s|es)?\b", used, re.IGNORECASE):
                    errors.append(f"{where}: E-term: `{bad}`; the glossary term is `{term}`")
            for m in HEDGE_RE.finditer(used):
                warnings.append(f"{where}: W-hedge: `{m.group(1)}`; write must, can, "
                                "or state the fact")
            for m in PASSIVE_RE.finditer(used):
                if m.group(2).lower() not in NOT_PARTICIPLE:
                    warnings.append(f"{where}: W-passive: `{m.group(0)}`; say who acts")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Check human-facing prose against the writing standard.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--glossary", default=None)
    args = parser.parse_args()
    glossary = Path(args.glossary) if args.glossary else Path("kb/GLOSSARY.md")
    if args.glossary and not glossary.is_file():
        print(f"{glossary}: E-missing: no glossary")
        return 1
    rejected = glossary_terms(glossary)

    errors, warnings = [], []
    for f in args.files:
        if f == "-":
            text = sys.stdin.read()
        elif Path(f).is_file():
            text = Path(f).read_text(encoding="utf-8")
        else:
            errors.append(f"{f}: E-missing: no such file")
            continue
        e, w = check(f, text, rejected)
        errors += e
        warnings += w
    for message in errors + warnings:
        print(message)
    print(f"ste-check: {len(args.files)} files, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
