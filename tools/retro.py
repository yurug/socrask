#!/usr/bin/env python3
"""retro — a retrospective at each milestone and iteration, from the harness telemetry.

The harness only improves if someone looks at how it behaved. At each completed
milestone, this tool puts the numbers of that milestone in one file: first-
attempt acceptance, repair loops, tokens per task against the previous
milestone, tool errors, and how often each harness check failed. The agent and
the engineer write one finding per signal worth acting on, and give each
finding a disposition. A `change:` names the metric it should move
(`metric: first-attempt`), and the next retrospective of the same kind shows
that metric then and now, so a change that did not help is seen.

Usage:
    retro.py record GATE --exit N [--seconds S]   append a gate result to the journal
    retro.py draft PERIOD [--write]               the numbers for one milestone or iteration
    retro.py check                                the gate, for CI

    --root     defaults to .
    --meter    defaults to kb/work/meter.jsonl (written by task-meter.py)
    --ledger   defaults to kb/work/ledger.json
    --journal  defaults to <git common dir>/socrask/checks.jsonl

Sources:
    meter      per task: tokens, active time, tool calls and errors, harness
               scripts that the agent ran and how many failed
    ledger     per task: first result and failed observations; per milestone:
               its tasks and its `retrospective` file
    journal    every gate that a local CI run recorded, inside or outside an
               agent session. It is per clone and not versioned.

PERIOD is `<project>/<id>` or an ID that is unique in the ledger: a roadmap
milestone, or an entry of the ledger's `iterations`. The previous period is the
one before it in the same project and of the same kind.

Metrics that a `metric:` can name: first-attempt (percent of tasks accepted on
the first observation), repair-loops (tasks with two or more failures),
tokens:<tier> (median per task), active-time (median minutes per task),
tool-errors:<tool> and script:<harness script> (failure percent). `draft --write` creates kb/work/retros/<YYYY-MM-DD>-<milestone>.md, or
refreshes the generated block of the existing file.

A retrospective file holds these lines and table:
    Milestone: <project>/<id>        (or Iteration: <project>/<id>)
    | ID | Signal | Cause | Disposition |
Each Disposition starts with `change:` (the commit, task or KB file that acts
on it), `reject:` (the reason) or `kit:` (the kit proposal). A file without a
finding says `No findings: <reason>`.

Checks (E = error, W = warning):
    E-due     a milestone whose tasks are all closed has no existing
              `retrospective` file
    E-retro   a retrospective without Milestone, without findings, or with a
              finding whose disposition is missing or unknown
    W-stale   a retrospective without the generated block
    W-metric  a `change:` disposition that names no `metric:`

What this does NOT do: judge a cause or a fix, or tell a check that failed
because it caught a defect from one that failed for nothing. The discussion
does that. Gates that run only in a remote CI do not reach the journal.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

BEGIN, END = "<!-- retro.py:begin -->", "<!-- retro.py:end -->"
DISPOSITIONS = ("change:", "reject:", "kit:")


def load_meter():
    """The meter's readers, so both tools agree on what a task consumed."""
    spec = importlib.util.spec_from_file_location("task_meter", Path(__file__).with_name("task-meter.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


meter = load_meter()


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()


def journal_path(args):
    if args.journal:
        return Path(args.journal)
    common = git(args.root, "rev-parse", "--git-common-dir")
    return (Path(args.root) / common / "socrask" / "checks.jsonl") if common else None


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def load_ledger(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def milestones(ledger):
    """[(project id, milestone)] in roadmap order."""
    return [(p["id"], m) for p in ledger.get("projects", [])
            for m in p.get("roadmap", {}).get("milestones", [])]


def iterations(ledger):
    """[(project id, iteration)] in start order; an iteration has no roadmap entry."""
    rows = sorted(ledger.get("iterations", []), key=lambda i: (str(i.get("start", "9999")), i.get("id", "")))
    return [(i.get("project"), i) for i in rows]


def periods(ledger):
    return [(p, m, "Milestone") for p, m in milestones(ledger)] + \
           [(p, i, "Iteration") for p, i in iterations(ledger)]


def find(ledger, ref):
    found = [(p, m, kind) for p, m, kind in periods(ledger) if ref in (m.get("id"), f"{p}/{m.get('id')}")]
    return found[0] if len(found) == 1 else None


def previous(ledger, project, period, kind):
    same = [m for p, m, k in periods(ledger) if p == project and k == kind]
    i = same.index(period)
    return same[i - 1] if i else None


def metrics(ids, summary, quality):
    """The values that a finding's `metric:` can name, for one period's tasks."""
    tasks = {k: t for k, t in summary.items() if k in ids and t["spans"]}
    out = {}
    judged = [quality[t] for t in ids if t in quality]
    if judged:
        out["first-attempt"] = 100 * sum(q[0] == "accepted" for q in judged) // len(judged)
    out["repair-loops"] = sum(1 for t in ids if t in quality and quality[t][1] >= 2)
    for tier, med in tier_medians(tasks).items():
        out[f"tokens:{tier}"] = med
    if tasks:
        out["active-time"] = int(statistics.median(t["active_s"] for t in tasks.values()) // 60)
    for key, prefix in (("tools", "tool-errors:"), ("checks", "script:")):
        for name, (n, bad) in merge(tasks, key):
            out[prefix + name] = 100 * bad // n if n else 0
    return out


def findings(path):
    """[(id, disposition)] from a retrospective file's findings table."""
    rows, lines = [], path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if [c.lower() for c in cells(line)][:4] == ["id", "signal", "cause", "disposition"]:
            rows = [cells(r) + [""] * 4 for r in lines[i + 2:] if r.lstrip().startswith("|")]
    return [(r[0], r[3].strip("` ")) for r in rows]


METRIC_RE = re.compile(r"metric:\s*([\w:.@/-]+)")


def rate(bad, n):
    return f"{bad}/{n} ({100 * bad // n}%)" if n else "0/0"


def tier_medians(tasks):
    by_tier = {}
    for t in tasks.values():
        by_tier.setdefault(t["tier"] or "untiered", []).append(t["total"])
    return {tier: int(statistics.median(v)) for tier, v in by_tier.items()}


def merge(tasks, key):
    out = {}
    for t in tasks.values():
        for name, (n, bad) in t[key].items():
            acc = out.setdefault(name, [0, 0])
            acc[0] += n
            acc[1] += bad
    return sorted(out.items(), key=lambda kv: (-kv[1][1], -kv[1][0], kv[0]))


def draft(args, ledger, project, milestone, kind="Milestone"):
    ids = milestone.get("tasks", [])
    events = meter.read_events(Path(args.root) / args.meter)
    summary = meter.tasks_summary(events)
    tasks = {k: t for k, t in summary.items() if k in ids and t["spans"]}
    quality = meter.quality(Path(args.root) / args.ledger)
    lines = [f"Numbers for {project}/{milestone.get('id')}: {len(ids)} tasks, {len(tasks)} metered.", ""]

    judged = [quality[t] for t in ids if t in quality]
    first = sum(q[0] == "accepted" for q in judged)
    lines.append(f"- First-attempt acceptance: {rate(first, len(judged))} of the tasks with feedback.")
    loops = [t for t in ids if t in quality and quality[t][1] >= 2]
    lines.append(f"- Repair loops (two or more failed observations): {', '.join(loops) or 'none'}.")

    before = previous(ledger, project, milestone, kind)
    old = {k: t for k, t in summary.items() if before and k in before.get("tasks", []) and t["spans"]}
    now, then = tier_medians(tasks), tier_medians(old)
    for tier, med in sorted(now.items()):
        trend = f", previous {kind.lower()} {meter.human(then[tier])}" if tier in then else ""
        lines.append(f"- Median tokens per {tier} task: {meter.human(med)}{trend}.")
    agents = {}
    for t in tasks.values():
        for a in t["agents"]:
            acc = agents.setdefault((a["runtime"], a["model"], a["role"]), [0, 0])
            acc[0] += a["requests"]
            acc[1] += sum(a[c] for c in meter.CLASSES)
    if agents:
        total = sum(v[1] for v in agents.values()) or 1
        top = sorted(agents.items(), key=lambda kv: -kv[1][1])[:5]
        lines.append("- Tokens by agent: " + "; ".join(
            f"{m} ({role}, {r}) {100 * n // total}%" for (r, m, role), (_, n) in top) + ".")
    if tasks:
        active = statistics.median(t["active_s"] for t in tasks.values()) // 60
        lines.append(f"- Median active time per task: {int(active)} min.")
    unmeasured = [k for k, t in tasks.items() if t["unmeasured"]]
    if unmeasured:
        lines.append(f"- Unmeasured tasks (no usage found): {', '.join(unmeasured)}.")
    if before and before.get("retrospective") and (Path(args.root) / before["retrospective"]).is_file():
        now_m = metrics(ids, summary, quality)
        then_m = metrics(before.get("tasks", []), summary, quality)
        follow = []
        for fid, disposition in findings(Path(args.root) / before["retrospective"]):
            m = METRIC_RE.search(disposition)
            if disposition.startswith("change:") and m:
                name = m.group(1)
                follow.append(f"  - {fid} ({name}): {then_m.get(name, 'n/a')} then, {now_m.get(name, 'n/a')} now.")
        if follow:
            lines += [f"- Changes decided at {project}/{before.get('id')}, and their metric:"] + follow
    notes = [f"{k} ({t['retro']})" for k, t in tasks.items() if t["retro"]]
    if notes:
        lines.append(f"- Task retrospectives: {'; '.join(notes)}.")

    tools = merge(tasks, "tools")
    if tools:
        lines += ["", "| Tool | Calls | Errors |", "|---|---|---|"]
        lines += [f"| {name} | {n} | {rate(bad, n)} |" for name, (n, bad) in tools[:8]]
    checks = merge(tasks, "checks")
    if checks:
        lines += ["", "| Harness script (agent sessions) | Runs | Failed |", "|---|---|---|"]
        lines += [f"| {name} | {n} | {rate(bad, n)} |" for name, (n, bad) in checks]

    starts = [e["at"] for e in events if e["task"] in ids and e["event"] == "start"]
    stops = [e["at"] for e in events if e["task"] in ids and e["event"] == "stop"]
    path = journal_path(args)
    if starts and stops and path and path.is_file():
        lo, hi = meter.parse_time(min(starts)), meter.parse_time(max(stops))
        gates = {}
        for e in meter.read_events(path):
            if lo <= meter.parse_time(e["at"]) <= hi:
                g = gates.setdefault(e["gate"], [0, 0, []])
                g[0] += 1
                g[1] += e["exit"] != 0
                g[2].append(e.get("seconds", 0))
        if gates:
            lines += ["", "| Gate (local CI journal) | Runs | Failed | Median s |", "|---|---|---|---|"]
            lines += [f"| {name} | {n} | {rate(bad, n)} | {statistics.median(s):.0f} |"
                      for name, (n, bad, s) in sorted(gates.items(), key=lambda kv: (-kv[1][1], kv[0]))]
    return "\n".join(lines)


def write(args, ref, block, kind="Milestone"):
    retros = Path(args.root) / "kb/work/retros"
    slug = ref.replace("/", "-")
    existing = sorted(retros.glob(f"*-{slug}.md"))
    if existing:
        path = existing[-1]
        text = path.read_text(encoding="utf-8")
        if BEGIN in text and END in text:
            head, rest = text.split(BEGIN, 1)
            text = head + BEGIN + "\n" + block + "\n" + END + rest.split(END, 1)[1]
            path.write_text(text, encoding="utf-8")
            return path
    else:
        retros.mkdir(parents=True, exist_ok=True)
        path = retros / f"{datetime.now(timezone.utc):%Y-%m-%d}-{slug}.md"
    path.write_text(f"""# Retrospective: {ref}

{kind}: {ref}

{BEGIN}
{block}
{END}

## Findings

One row per signal worth acting on. Disposition: `change: <commit, task or KB file>;
metric: <the metric it should move>`, `reject: <reason>` or `kit: <proposal>`. Ask also which operation the agents did by hand
more than once: each one is a finding, and its change is a tool in `kb/conventions/tools.md`.

| ID | Signal | Cause | Disposition |
|---|---|---|---|
""", encoding="utf-8")
    return path


def check(args, ledger):
    errors, warnings = [], []
    root = Path(args.root)
    status = {t["id"]: t.get("status") for t in ledger.get("tasks", [])}
    for project, m in milestones(ledger):  # closed iterations: project-check.py checks theirs
        tasks = m.get("tasks", [])
        if tasks and all(status.get(t) == "closed" for t in tasks):
            ref = m.get("retrospective", "")
            if not (ref and (root / ref).is_file()):
                errors.append(f"E-due: milestone {project}/{m.get('id')} is complete without an existing "
                              f"retrospective (`retro.py draft {project}/{m.get('id')} --write`)")
    for f in sorted((root / "kb/work/retros").glob("*.md")):
        text, rel = f.read_text(encoding="utf-8"), f.relative_to(root)
        if not re.search(r"^(Milestone|Iteration):\s*\S+", text, re.MULTILINE):
            errors.append(f"E-retro: {rel} has no Milestone: or Iteration: <project>/<id>")
        if BEGIN not in text:
            warnings.append(f"W-stale: {rel} has no generated block; run `retro.py draft ... --write`")
        rows, lines = [], text.splitlines()
        for i, line in enumerate(lines):
            if [c.lower() for c in cells(line)][:4] == ["id", "signal", "cause", "disposition"]:
                rows = [cells(r) + [""] * 4 for r in lines[i + 2:] if r.lstrip().startswith("|")]
        if not rows and not re.search(r"^No findings:\s*\S+", text, re.MULTILINE):
            errors.append(f"E-retro: {rel} has no finding and no `No findings: <reason>` line")
        for fid, _, _, disposition, *_ in rows:
            d = disposition.strip("` ")
            if not (d.startswith(DISPOSITIONS) and d.split(":", 1)[1].strip()):
                errors.append(f"E-retro: {rel} finding {fid or '?'} needs a disposition: "
                              "change: <ref>, reject: <reason> or kit: <proposal>")
            elif d.startswith("change:") and not METRIC_RE.search(d):
                warnings.append(f"W-metric: {rel} finding {fid or '?'} changes something but names no "
                                "`metric:`; the next retrospective cannot tell whether it helped")
    for m in errors + warnings:
        print(m)
    print(f"retro: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description="Milestone and iteration retrospectives from the harness telemetry.")
    ap.add_argument("command", choices=["record", "draft", "check"])
    ap.add_argument("target", nargs="?", help="GATE for record, MILESTONE or ITERATION for draft")
    ap.add_argument("--exit", type=int, dest="code")
    ap.add_argument("--seconds", type=float, default=0)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--root", default=".")
    ap.add_argument("--meter", default="kb/work/meter.jsonl")
    ap.add_argument("--ledger", default="kb/work/ledger.json")
    ap.add_argument("--journal")
    args = ap.parse_args()

    if args.command == "record":
        if not args.target or args.code is None:
            ap.error("record needs GATE and --exit N")
        path = journal_path(args)
        if not path:
            print("retro: no Git repository and no --journal; nothing recorded")
            return 0
        meter.append(path, {"gate": args.target, "exit": args.code, "seconds": round(args.seconds, 1),
                            "at": meter.now(), "commit": git(args.root, "rev-parse", "--short", "HEAD")})
        return 0
    ledger = load_ledger(Path(args.root) / args.ledger)
    if args.command == "check":
        return check(args, ledger)
    if not args.target:
        ap.error("draft needs a MILESTONE or an ITERATION")
    found = find(ledger, args.target)
    if not found:
        print(f"retro: no single milestone or iteration {args.target} in {args.ledger}")
        return 1
    project, milestone, kind = found
    block = draft(args, ledger, project, milestone, kind)
    if args.write:
        print(f"wrote {write(args, project + '/' + milestone.get('id', ''), block, kind)}")
    else:
        print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
