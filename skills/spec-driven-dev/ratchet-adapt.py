#!/usr/bin/env python3
"""ratchet-adapt — turn structured runner output into ratchet.py results.

ratchet.py accepts only complete, structured results (docs/ratchet.md). Most
runners can already write one of three structured formats; this adapter
converts them, so a project can ratchet without scraping console logs.

Usage:
    ratchet-adapt.py junit FILE...   JUnit XML (pytest, jest, dune, cargo2junit...)
    ratchet-adapt.py tap FILE...     TAP version 12/13
    ratchet-adapt.py steps FILE      CI step receipt: {"complete": bool,
                                     "steps": [{"name", "status", "job"?}]}
    ... > results.json && ratchet.py --from-results results.json

Obligations:
    - a test whose name starts with a property ID (`P3: ...`, `T-2 ...`) reports
      that property;
    - otherwise it reports its suite as `S-<slug>`: the JUnit testsuite, the TAP
      file, or the CI step. A suite-level obligation is weaker evidence: it says
      the suite passed, not which property holds. Refine by naming tests after
      properties.

Completeness: `complete` is false when the source says the run did not finish
(no JUnit testcase, a TAP plan that does not match or "Bail out!",
a receipt with complete != true or a step still queued or running).

What this does NOT do: detect a runner that omits failing tests from its own
report. The runner's report is the trust boundary.
"""
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

PROPERTY_RE = re.compile(r"^\s*((?:P|NF|T)-?\d+)\b")


def slug(text):
    s = re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-.")
    return ("S-" + (s or "suite"))[:82]


def obligation(name, suite):
    m = PROPERTY_RE.match(name)
    return m.group(1) if m else slug(suite)


def junit(paths):
    tests, complete = [], True
    for path in paths:
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else root.iter("testsuite")
        for suite in suites:
            sname = suite.get("name") or Path(path).stem
            for case in suite.iter("testcase"):
                name = case.get("name", "")
                cid = f"{case.get('classname', sname)}::{name}"
                if case.find("error") is not None or case.find("failure") is not None:
                    status = "failed"
                elif case.find("skipped") is not None:
                    status = "skipped"
                else:
                    status = "passed"
                tests.append({"id": cid, "obligation": obligation(name, sname), "status": status})
    if not tests:
        complete = False
    return tests, complete


def tap(paths):
    tests, complete = [], True
    for path in paths:
        sname, planned, seen = Path(path).stem, None, 0
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Bail out!"):
                complete = False
            m = re.match(r"^1\.\.(\d+)", line)
            if m:
                planned = int(m.group(1))
            m = re.match(r"^(not ok|ok)\b\s*(\d+)?\s*-?\s*(.*)$", line)
            if not m:
                continue
            seen += 1
            desc, directive = (m.group(3).split("#", 1) + [""])[:2]
            directive = directive.strip().lower()
            if directive.startswith("skip"):
                status = "skipped"
            elif m.group(1) == "ok" and not directive.startswith("todo"):
                status = "passed"
            else:
                status = "failed"
            tests.append({"id": f"{sname}::{m.group(2) or seen}::{desc.strip()}",
                          "obligation": obligation(desc, sname), "status": status})
        if planned is None or planned != seen:
            complete = False
    return tests, complete


def steps(paths):
    data = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
    rows = data.get("steps", [])
    complete = data.get("complete") is True and bool(rows)
    tests = []
    for row in rows:
        status = str(row.get("status", "")).lower()
        if status in ("queued", "running", "pending", ""):
            complete = False
            continue
        # A step name repeats across jobs; the job keeps their obligations apart.
        name = " ".join(filter(None, (row.get("job"), row.get("name")))) or "?"
        tests.append({"id": name, "obligation": obligation(row.get("name", ""), name),
                      "status": {"passed": "passed", "success": "passed", "skipped": "skipped"}.get(status, "failed")})
    return tests, complete


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("junit", "tap", "steps"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        tests, complete = {"junit": junit, "tap": tap, "steps": steps}[sys.argv[1]](sys.argv[2:])
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"ratchet-adapt: {exc}", file=sys.stderr)
        return 2
    seen = {}
    for t in tests:  # ratchet.py rejects duplicate IDs; number repeats in run order
        seen[t["id"]] = seen.get(t["id"], 0) + 1
        if seen[t["id"]] > 1:
            t["id"] = f"{t['id']}#{seen[t['id']]}"
    json.dump({"version": 1, "complete": complete, "tests": tests}, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
