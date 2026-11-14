#!/usr/bin/env python3
"""insights — which agent, at what cost, for which result, over the project's history.

The meter records each task's requests by runtime, model and role; the ledger
records each task's outcome. A retrospective compares one period with the one
before it. This tool reads the whole history and answers the questions that
improve the process itself: which models and roles spend the tokens, which
lead model gets accepted on the first attempt for which tier, how cost, cycle
time and estimates move from one iteration to the next, and where a cheaper
model has earned a trial.

Usage:
    insights.py [--meter kb/work/meter.jsonl] [--ledger kb/work/ledger.json]
                [--prices kb/work/prices.json] [--min-tasks 5] [--check]

Sections:
    Coverage   metered tasks, unmeasured ones, and tasks whose windows share a root
    Agents     requests and tokens by runtime, model and role
    Outcomes   per lead model and tier: tasks, first-attempt acceptance, repair
               loops, median tokens (and cost), median active time
    Periods    per iteration (or per ISO week without iterations): tasks,
               acceptance, median tokens, median cycle time from first start to
               first acceptance, and the estimate ratios
    Hints      a tier where a cheaper lead model has at least --min-tasks judged
               tasks and a first-attempt rate within 10 points of the best one

The lead model of a task is the model of its main agent with the most requests.
First-attempt acceptance counts the tasks whose first feedback event is
`accepted`, among the tasks with feedback. Costs need a prices file, in dollars
per million tokens; a model matches the longest key that it contains:

    {"claude-opus": {"input": 15, "cache_read": 1.5, "cache_write": 18.75, "output": 75}}

Without prices, the tool compares tokens only within one model, and gives no hint.

Exit code: 0, or 1 with --check when more than 10% of the last 20 metered tasks are
unmeasured (E-coverage) or absent from the ledger (E-ledger): an analysis of
missing data misleads.

What this does NOT do: tell whether a task class is comparable across models
(the hints are trials to run, not decisions), price tokens by itself, or see
work that was never metered.
"""
import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import statistics
import sys


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


meter = load("task_meter", "task-meter.py")


def ledger_rows(path):
    """Tasks and iterations from the ledger and its archive."""
    tasks, iterations = {}, []
    path = Path(path)
    for p in (path, path.with_name(path.stem + "-archive.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        tasks.update({t["id"]: t for t in data.get("tasks", []) if isinstance(t, dict) and "id" in t})
        iterations += [i for i in data.get("iterations", []) if isinstance(i, dict)]
    return tasks, sorted(iterations, key=lambda i: str(i.get("start", "")))


def price_of(prices, model):
    keys = [k for k in prices if k in model]
    return prices[max(keys, key=len)] if keys else None


def cost(prices, agents):
    """Dollars for a task's agents, or None when a model has no price."""
    total = 0.0
    for a in agents:
        p = price_of(prices, a["model"])
        if p is None:
            return None
        total += sum(a[c] * p.get(c, 0) for c in meter.CLASSES) / 1e6
    return total


def lead(agents):
    main = [a for a in agents if a["role"] == "main"] or agents
    if not main:
        return None
    a = max(main, key=lambda a: a["requests"])
    return f"{a['runtime']}:{a['model']}"


def med(values, fmt=str):
    values = [v for v in values if v is not None]
    return fmt(statistics.median(values)) if values else "-"


def pct(part, whole):
    return f"{100 * part // whole}% of {whole}" if whole else "-"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def main():
    ap = argparse.ArgumentParser(description="Which agent, at what cost, for which result.")
    ap.add_argument("--meter", default="kb/work/meter.jsonl")
    ap.add_argument("--ledger", default="kb/work/ledger.json")
    ap.add_argument("--prices", default="kb/work/prices.json")
    ap.add_argument("--min-tasks", type=int, default=5)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    summary = {k: t for k, t in meter.tasks_summary(meter.read_events(Path(args.meter))).items() if t["spans"]}
    quality = meter.quality(args.ledger)
    ledger_tasks, iterations = ledger_rows(args.ledger)
    try:
        prices = json.loads(Path(args.prices).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prices = {}

    rows = {}
    for task, t in summary.items():
        first, failed, accepted = quality.get(task, (None, 0, None))
        rows[task] = {
            "tier": t["tier"] or "untiered", "lead": lead(t["agents"]), "tokens": t["total"],
            "cost": cost(prices, t["agents"]) if prices and t["agents"] else None,
            "active": t["active_s"] / 60, "first": first, "failed": failed,
            "cycle": (meter.parse_time(accepted) - meter.parse_time(t["first"])).total_seconds() / 3600
            if accepted else None,
            "budget": t["total"] / t["budget"] if t["budget"] and t["total"] else None,
            "estimate": (t["active_s"] / 3600) / ledger_tasks[task]["estimate_hours"]
            if ledger_tasks.get(task, {}).get("estimate_hours") else None,
            "unmeasured": bool(t["unmeasured"]), "started": t["first"],
            "closed": ledger_tasks.get(task, {}).get("status") == "closed",
        }

    out = ["## Coverage", ""]
    unmeasured = [k for k, r in rows.items() if r["unmeasured"]]
    shared = sum(1 for t in summary.values() for o in summary.values() if t is not o and any(
        r1 == r2 and a1 < b2 and a2 < b1 for a1, b1, r1 in t["windows"] for a2, b2, r2 in o["windows"])) // 2
    out.append(f"{len(rows)} metered tasks, {len(unmeasured)} unmeasured, {shared} pairs share a root window.")
    if ledger_tasks:
        absent = [k for k in rows if k not in ledger_tasks]
        judged = [k for k, r in rows.items() if r["first"] or r["closed"]]
        out.append(f"{len(absent)} metered tasks are absent from the ledger; {len(judged)} have a result "
                   "(a feedback event or a closed status). A cost without a result says little.")

    agents = {}
    for t in summary.values():
        for a in t["agents"]:
            acc = agents.setdefault((a["runtime"], a["model"], a["role"]), {"requests": 0, "tokens": 0, "cost": 0.0})
            acc["requests"] += a["requests"]
            acc["tokens"] += sum(a[c] for c in meter.CLASSES)
            p = price_of(prices, a["model"]) if prices else None
            acc["cost"] = None if acc["cost"] is None or p is None else \
                acc["cost"] + sum(a[c] * p.get(c, 0) for c in meter.CLASSES) / 1e6
    if agents:
        total = sum(a["tokens"] for a in agents.values()) or 1
        out += ["", "## Agents", ""] + table(
            ["Runtime", "Model", "Role", "Requests", "Tokens", "Share", "Cost"],
            [(r, m, role, a["requests"], meter.human(a["tokens"]), f"{100 * a['tokens'] // total}%",
              f"${a['cost']:.2f}" if a["cost"] is not None else "-")
             for (r, m, role), a in sorted(agents.items(), key=lambda kv: -kv[1]["tokens"])])

    groups = {}
    for r in rows.values():
        if r["lead"]:
            groups.setdefault((r["lead"], r["tier"]), []).append(r)
    stats = {}
    for key, rs in groups.items():
        judged = [r for r in rs if r["first"]]
        stats[key] = (len(judged), sum(r["first"] == "accepted" for r in judged),
                      med([r["cost"] for r in rs], float) if prices else None)
    if groups:
        out += ["", "## Outcomes", ""] + table(
            ["Lead model", "Tier", "Tasks", "Closed", "First-attempt", "Repair loops", "Median tokens",
             "Median cost", "Median active min"],
            [(model, tier, len(rs), sum(r["closed"] for r in rs), pct(stats[(model, tier)][1], stats[(model, tier)][0]),
              sum(r["failed"] >= 2 for r in rs), med([r["tokens"] for r in rs], lambda v: meter.human(int(v))),
              med([r["cost"] for r in rs], lambda v: f"${v:.2f}"), med([r["active"] for r in rs], lambda v: f"{v:.0f}"))
             for (model, tier), rs in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0]))])

    periods = []
    for it in iterations:
        ids = set(it.get("tasks", []))
        periods.append((f"{it.get('id')} ({it.get('status', '?')})", [r for k, r in rows.items() if k in ids]))
    if not periods:
        weeks = {}
        for r in rows.values():
            y, w, _ = datetime.fromisoformat(r["started"].replace("Z", "+00:00")).isocalendar()
            weeks.setdefault(f"{y}-W{w:02d}", []).append(r)
        periods = sorted(weeks.items())
    if periods:
        out += ["", "## Periods", ""] + table(
            ["Period", "Tasks", "First-attempt", "Median tokens", "Median cycle h", "Budget ratio",
             "Estimate ratio"],
            [(name, len(rs), pct(sum(r["first"] == "accepted" for r in rs), sum(bool(r["first"]) for r in rs)),
              med([r["tokens"] for r in rs if not r["unmeasured"]], lambda v: meter.human(int(v))),
              med([r["cycle"] for r in rs], lambda v: f"{v:.1f}"), med([r["budget"] for r in rs], lambda v: f"{v:.1f}x"),
              med([r["estimate"] for r in rs], lambda v: f"{v:.1f}x")) for name, rs in periods])

    hints = []
    if prices:
        for tier in sorted({t for _, t in stats}):
            cands = [(m, n, ok, c) for (m, t), (n, ok, c) in stats.items()
                     if t == tier and n >= args.min_tasks and c not in (None, "-")]
            if len(cands) < 2:
                continue
            best = max(100 * ok / n for _, n, ok, _ in cands)
            costly = max(float(c) for *_, c in cands)
            for m, n, ok, c in cands:
                if float(c) < costly and 100 * ok / n >= best - 10:
                    hints.append(f"- {tier}: {m} accepts {100 * ok // n}% on the first attempt ({n} tasks) at a "
                                 f"median ${float(c):.2f} per task, against ${costly:.2f} for the costliest lead. "
                                 "Validate it on this task class (references/model-routing.md).")
    out += ["", "## Hints", ""] + (hints or [
        "No hint: " + ("no tier has two priced lead models with enough judged tasks." if prices
                       else f"no prices file ({args.prices}), so models are not compared by cost.")])
    print("\n".join(out))

    recent = sorted(rows.items(), key=lambda kv: kv[1]["started"])[-20:]
    bad = sum(r["unmeasured"] for _, r in recent)
    orphans = sum(k not in ledger_tasks for k, _ in recent) if ledger_tasks else 0
    code = 0
    if args.check and recent and bad * 10 > len(recent):
        print(f"E-coverage: {bad} of the last {len(recent)} metered tasks are unmeasured; "
              "fix the attribution (task-meter.py remeasure) before reading these numbers")
        code = 1
    if args.check and recent and orphans * 10 > len(recent):
        print(f"E-ledger: {orphans} of the last {len(recent)} metered tasks are absent from the ledger; "
              "their cost has no result to join")
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
