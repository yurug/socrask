#!/usr/bin/env python3
"""source-check — external sources are read on time, and every item is placed.

Slack channels, user feedback, Linear or GitHub issues carry project
knowledge that the KB does not have yet. `kb/work/sources.json` declares each
source with an owner, a cadence and a cursor. Each sync writes a digest in
`kb/sources/digests/<source>-<YYYY-MM-DD>.md` that gives every new item a
disposition. The procedure is in the spec-driven-dev skill,
references/external-sources.md.

Usage:
    source-check.py [--sources kb/work/sources.json] [--today YYYY-MM-DD]
    source-check.py --due      list overdue sources (for a SessionStart hook)

sources.json:
    {"version": 1, "kb_visibility": "private|public",
     "sources": [{"id", "kind", "locator", "owner", "via", "cadence_days",
                  "visibility": "internal|public", "cursor", "last_synced"}]}

Digest table: | Item | Link | Disposition | Ref |, where Disposition is
    feedback  Ref is a feedback ID in kb/work/ledger.json
    fact      Ref is the KB file that now records it (as imported-unverified)
    question  Ref is forebrief:<card-id>
    noise     Ref can be empty

Exit code: 0 = clean (warnings allowed), 1 = errors. `--due` always exits 0.

Checks (E = error, W = warning):
    E-schema    a source without id, kind, locator, owner, via, a positive
                cadence_days, or a visibility of internal/public
    E-exposure  an internal source while the KB is declared public
    E-digest    a synced source without the digest of its last sync, a digest
                row with an unknown disposition, or a Ref that does not resolve
    W-overdue   a source not synced within its cadence

What this does NOT check: that items were understood correctly, that nothing
was paraphrased too closely, or that the cursor matches the source.
"""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys

REQUIRED = ("id", "kind", "locator", "owner", "via")
DISPOSITIONS = {"feedback", "fact", "question", "noise"}


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def digest_rows(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and [c.lower() for c in cells(line)][:4] == \
                ["item", "link", "disposition", "ref"]:
            return [dict(zip(("item", "link", "disposition", "ref"), cells(r) + [""] * 4))
                    for r in lines[i + 2:] if r.lstrip().startswith("|")]
    return None


def due(source, today):
    last = source.get("last_synced")
    if not last:
        return True
    return date.fromisoformat(last) + timedelta(days=float(source["cadence_days"])) <= today


def main():
    ap = argparse.ArgumentParser(description="Check external project sources and their digests.")
    ap.add_argument("--sources", default="kb/work/sources.json")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--due", action="store_true")
    args = ap.parse_args()
    path, today = Path(args.sources), date.fromisoformat(args.today)
    if not path.is_file():
        if args.due:
            return 0
        print(f"{path}: no external sources declared")
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"{path}: E-schema: not JSON: {exc}")
        return 0 if args.due else 1
    root = path.parent.parent.parent  # kb/work/sources.json -> repo root
    sources = data.get("sources", [])

    if args.due:
        late = [s for s in sources if s.get("id") and s.get("cadence_days") and due(s, today)]
        for s in late:
            print(f"Source {s['id']} ({s.get('kind')}, {s.get('locator')}) is due: last synced "
                  f"{s.get('last_synced') or 'never'}, cadence {s['cadence_days']} days, owner "
                  f"{s.get('owner')}. Sync it by references/external-sources.md before other work, "
                  "or tell the user it is overdue.")
        return 0

    errors, warnings = [], []
    if data.get("kb_visibility") not in ("private", "public"):
        errors.append("E-schema: kb_visibility must be private or public")
    ledger_ids = set()
    ledger = root / "kb/work/ledger.json"
    if ledger.is_file():
        try:
            ledger_ids = {f.get("id") for f in json.loads(ledger.read_text()).get("feedback", [])}
        except ValueError:
            pass
    for s in sources:
        sid = s.get("id", "?")
        missing = [k for k in REQUIRED if not s.get(k)]
        if missing:
            errors.append(f"E-schema: source {sid} lacks {', '.join(missing)}")
        if not isinstance(s.get("cadence_days"), (int, float)) or s["cadence_days"] <= 0:
            errors.append(f"E-schema: source {sid} needs a positive cadence_days")
            continue
        if s.get("visibility") not in ("internal", "public"):
            errors.append(f"E-schema: source {sid} visibility must be internal or public")
        elif s["visibility"] == "internal" and data.get("kb_visibility") == "public":
            errors.append(f"E-exposure: internal source {sid} feeds a public KB; "
                          "keep its knowledge out of this KB or make the KB private")
        if due(s, today):
            warnings.append(f"W-overdue: source {sid} last synced {s.get('last_synced') or 'never'}, "
                            f"cadence {s['cadence_days']} days")
        if not s.get("last_synced"):
            continue
        digest = root / "kb/sources/digests" / f"{sid}-{s['last_synced']}.md"
        if not digest.is_file():
            errors.append(f"E-digest: source {sid} synced {s['last_synced']} without "
                          f"{digest.relative_to(root)}")
            continue
        rows = digest_rows(digest.read_text(encoding="utf-8"))
        if rows is None:
            errors.append(f"E-digest: {digest.relative_to(root)} has no Item | Link | Disposition | Ref table")
            continue
        for r in rows:
            disp, ref = r["disposition"].lower(), r["ref"].strip("` ")
            where = f"{digest.relative_to(root)} item `{r['item']}`"
            if disp not in DISPOSITIONS:
                errors.append(f"E-digest: {where} has disposition `{r['disposition']}`")
            elif disp == "feedback" and ref not in ledger_ids:
                errors.append(f"E-digest: {where} cites feedback `{ref}`, absent from the ledger")
            elif disp == "fact" and not (ref and (root / ref.split("#")[0]).is_file()):
                errors.append(f"E-digest: {where} cites KB file `{ref}`, which does not exist")
            elif disp == "question" and not re.match(r"^forebrief:\S+$", ref):
                errors.append(f"E-digest: {where} needs Ref forebrief:<card-id>")
    for m in errors + warnings:
        print(f"{path}: {m}")
    print(f"source-check: {len(sources)} sources, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
