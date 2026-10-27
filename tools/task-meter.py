#!/usr/bin/env python3
"""task-meter — tokens, time and tool calls per task, next to the quality signals.

"Cost per accepted task, including repair and review" needs a measurement.
The agent marks each ledger task with `start` and `stop`; the meter adds up the
token usage that the host recorded between the two marks. It reads usage
numbers, timestamps, tool names and error flags. From a shell command it keeps
only the name of a harness script under `tools/` or `skills/<skill>/`. It never
reads other message content.

Usage:
    task-meter.py start TASK [--tier direct|slice|full] [--budget 200k]
    task-meter.py stop TASK
    task-meter.py note TASK --retro "cause; fix: <harness or KB change>"
    task-meter.py report [--check] [--ledger kb/work/ledger.json]

    --meter        defaults to kb/work/meter.jsonl
    --session      Claude session ID; defaults to $CLAUDE_CODE_SESSION_ID
    --claude-dir   defaults to ~/.claude/projects
    --codex-dir    defaults to ~/.codex/sessions

Attribution: with a session ID, the messages of that session and its subagents
between the marks; without one (Codex), every message whose working directory
is the directory where `start` ran. Each API request counts once.

Report, per task: tokens by class, wall-clock and active time (gaps over five
minutes do not count), budget against actual, tool calls and errors, harness
script runs and failures, and from the ledger the first-attempt result and the
number of failed observations. A task whose total is
over twice the median of its tier (three or more earlier tasks) is an outlier.

`report --check` exits 1 when an outlier has no retrospective. It never fails
on cost alone: a budget gate would reward skipping verification.

What this does NOT do: tell useful tokens from wasted ones, separate two
sessions working in one directory without a session ID, or price tokens. A
failed command that runs two harness scripts counts a failure for both.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import statistics
import sys

CLASSES = ("input", "cache_read", "cache_write", "output")
IDLE_CAP = 300
# A harness script named in a shell command. The meter tools themselves are not checks.
SCRIPT_RE = re.compile(r"(?:^|[\s/;&|(\"'])(?:tools|skills/[\w-]+)/([\w.-]+\.(?:py|sh))\b")
NOT_CHECKS = {"task-meter.py", "retro.py"}
EXIT_RE = re.compile(r'"exit_code":\s*(-?\d+)')
BUDGET_RE = re.compile(r"^~?\s*(\d+(?:\.\d+)?)\s*([kKmM]?)\s*(?:tokens?)?$")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def parse_budget(text):
    m = BUDGET_RE.match(text.strip())
    if not m:
        return None
    scale = {"": 1, "k": 1e3, "m": 1e6}[m.group(2).lower()]
    return int(float(m.group(1)) * scale)


def human(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(n)


def read_events(meter):
    if not meter.is_file():
        return []
    return [json.loads(l) for l in meter.read_text(encoding="utf-8").splitlines() if l.strip()]


def append(meter, event):
    meter.parent.mkdir(parents=True, exist_ok=True)
    with meter.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def recent_files(root, pattern, since):
    if not root.is_dir():
        return []
    cutoff = since.timestamp() - 60
    return [p for p in root.glob(pattern) if p.stat().st_mtime >= cutoff]


def claude_usage(root, start, stop, session, cwd):
    """{request id: (time, model, {class: n})} from Claude Code transcripts."""
    found = {}
    files = recent_files(root, "*/*.jsonl", start) + recent_files(root, "*/*/subagents/*.jsonl", start)
    for path in files:
        for line in path.open(encoding="utf-8", errors="replace"):
            if '"usage"' not in line:
                continue
            try:
                rec = json.loads(line)
                usage, at = rec["message"]["usage"], parse_time(rec["timestamp"])
            except (ValueError, KeyError, TypeError):
                continue
            if not start <= at <= stop:
                continue
            if session and rec.get("sessionId") != session:
                continue
            if not session and not str(rec.get("cwd", "")).startswith(cwd):
                continue
            key = rec.get("requestId") or rec["message"].get("id") or f"{path}:{at}"
            found[key] = (at, rec["message"].get("model", "unknown"), {
                "input": usage.get("input_tokens", 0),
                "cache_read": usage.get("cache_read_input_tokens", 0),
                "cache_write": usage.get("cache_creation_input_tokens", 0),
                "output": usage.get("output_tokens", 0)})
    return found


def codex_usage(root, start, stop, cwd):
    """Same shape from Codex rollouts; attribution by working directory."""
    found = {}
    for path in recent_files(root, "**/*.jsonl", start):
        session_cwd, model = None, "codex"
        for n, line in enumerate(path.open(encoding="utf-8", errors="replace")):
            if '"session_meta"' in line or '"turn_context"' in line:
                try:
                    payload = json.loads(line)["payload"]
                    session_cwd = payload.get("cwd", session_cwd)
                    model = payload.get("model", model)
                except (ValueError, KeyError):
                    pass
            if '"token_count"' not in line or not str(session_cwd or "").startswith(cwd):
                continue
            try:
                rec = json.loads(line)
                last, at = rec["payload"]["info"]["last_token_usage"], parse_time(rec["timestamp"])
            except (ValueError, KeyError, TypeError):
                continue
            if start <= at <= stop:
                cached = last.get("cached_input_tokens", 0)
                found[f"{path}:{n}"] = (at, model, {
                    "input": last.get("input_tokens", 0) - cached, "cache_read": cached,
                    "cache_write": last.get("cache_write_input_tokens", 0),
                    "output": last.get("output_tokens", 0)})
    return found


def scripts(command):
    return sorted({m for m in SCRIPT_RE.findall(command) if m not in NOT_CHECKS})


def tally(calls):
    """{tool: [calls, errors]} and {script: [runs, failures]} from (name, scripts, failed)."""
    tools, checks = {}, {}
    for name, names, failed in calls:
        t = tools.setdefault(name, [0, 0])
        t[0] += 1
        t[1] += bool(failed)
        for s in names:
            c = checks.setdefault(s, [0, 0])
            c[0] += 1
            c[1] += bool(failed)
    return tools, checks


def claude_tools(root, start, stop, session, cwd):
    """[(tool, harness scripts, failed)] from Claude Code transcripts."""
    uses, failed = {}, set()
    files = recent_files(root, "*/*.jsonl", start) + recent_files(root, "*/*/subagents/*.jsonl", start)
    for path in files:
        for line in path.open(encoding="utf-8", errors="replace"):
            if '"tool_use"' not in line and '"tool_result"' not in line:
                continue
            try:
                rec = json.loads(line)
                at, content = parse_time(rec["timestamp"]), rec["message"]["content"]
            except (ValueError, KeyError, TypeError):
                continue
            if not start <= at <= stop or not isinstance(content, list):
                continue
            if session and rec.get("sessionId") != session:
                continue
            if not session and not str(rec.get("cwd", "")).startswith(cwd):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    command = str((b.get("input") or {}).get("command", ""))
                    uses[b.get("id")] = (b.get("name", "unknown"), scripts(command))
                elif b.get("type") == "tool_result" and b.get("is_error"):
                    failed.add(b.get("tool_use_id"))
    return [(name, names, key in failed) for key, (name, names) in uses.items()]


def codex_tools(root, start, stop, cwd):
    """Same shape from Codex rollouts; a call fails when an exit code is not 0."""
    uses, failed = {}, set()
    for path in recent_files(root, "**/*.jsonl", start):
        session_cwd = None
        for line in path.open(encoding="utf-8", errors="replace"):
            if '"session_meta"' in line or '"turn_context"' in line:
                try:
                    session_cwd = json.loads(line)["payload"].get("cwd", session_cwd)
                except (ValueError, KeyError, AttributeError):
                    pass
            if '_call' not in line or not str(session_cwd or "").startswith(cwd):
                continue
            try:
                rec = json.loads(line)
                p, at = rec["payload"], parse_time(rec["timestamp"])
            except (ValueError, KeyError, TypeError):
                continue
            if not start <= at <= stop or not isinstance(p, dict):
                continue
            key = (path, p.get("call_id"))
            if p.get("type") in ("function_call", "custom_tool_call"):
                text = str(p.get("input") or p.get("arguments") or "")
                uses[key] = (p.get("name", "unknown"), scripts(text))
            elif p.get("type") in ("function_call_output", "custom_tool_call_output"):
                out = p.get("output")
                text = " ".join(str(part.get("text", "")) for part in out if isinstance(part, dict)) \
                    if isinstance(out, list) else str(out)
                if any(int(c) != 0 for c in EXIT_RE.findall(text)):
                    failed.add(key)
    return [(name, names, key in failed) for key, (name, names) in uses.items()]


def measure(args, start_event, stop_at):
    start = parse_time(start_event["at"])
    stop = parse_time(stop_at)
    found = claude_usage(Path(args.claude_dir), start, stop, start_event.get("session"), start_event["cwd"])
    if not start_event.get("session"):
        found.update(codex_usage(Path(args.codex_dir), start, stop, start_event["cwd"]))
    by_model, times = {}, sorted(t for t, _, _ in found.values())
    for _, model, usage in found.values():
        totals = by_model.setdefault(model, dict.fromkeys(CLASSES, 0))
        for c in CLASSES:
            totals[c] += usage[c]
    active = sum(min((b - a).total_seconds(), IDLE_CAP) for a, b in zip(times, times[1:]))
    calls = claude_tools(Path(args.claude_dir), start, stop, start_event.get("session"), start_event["cwd"])
    if not start_event.get("session"):
        calls += codex_tools(Path(args.codex_dir), start, stop, start_event["cwd"])
    tools, checks = tally(calls)
    return {"usage": by_model, "requests": len(found), "tools": tools, "checks": checks,
            "wall_s": int((stop - start).total_seconds()), "active_s": int(active)}


def open_start(events, task):
    starts = [e for e in events if e["task"] == task and e["event"] in ("start", "stop")]
    return starts[-1] if starts and starts[-1]["event"] == "start" else None


def tasks_summary(events):
    tasks = {}
    for e in events:
        t = tasks.setdefault(e["task"], {"tier": None, "budget": None, "usage": {}, "requests": 0,
                                         "wall_s": 0, "active_s": 0, "first": e["at"], "retro": None,
                                         "spans": 0, "tools": {}, "checks": {}})
        if e["event"] == "start":
            t["tier"] = e.get("tier") or t["tier"]
            t["budget"] = e.get("budget") or t["budget"]
        elif e["event"] == "stop":
            t["spans"] += 1
            for k in ("requests", "wall_s", "active_s"):
                t[k] += e[k]
            for k in ("tools", "checks"):
                for name, (n, bad) in e.get(k, {}).items():
                    acc = t[k].setdefault(name, [0, 0])
                    acc[0] += n
                    acc[1] += bad
            for model, usage in e["usage"].items():
                totals = t["usage"].setdefault(model, dict.fromkeys(CLASSES, 0))
                for c in CLASSES:
                    totals[c] += usage[c]
        elif e["event"] == "note":
            t["retro"] = e["retro"]
    for t in tasks.values():
        t["total"] = sum(sum(u.values()) for u in t["usage"].values())
    return tasks


def quality(ledger):
    """{task: (first result, failed count, first accepted time)} from feedback events."""
    out = {}
    try:
        data = json.loads(Path(ledger).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return out
    for fb in data.get("feedback", []):
        evs = sorted(fb.get("events", []), key=lambda e: e.get("at", ""))
        if fb.get("task") and evs:
            accepted = [e["at"] for e in evs if e.get("result") == "accepted"]
            out[fb["task"]] = (evs[0].get("result"), sum(e.get("result") == "failed" for e in evs),
                               accepted[0] if accepted else None)
    return out


def report(args):
    tasks = {k: t for k, t in tasks_summary(read_events(Path(args.meter))).items() if t["spans"]}
    q = quality(args.ledger)
    ordered = sorted(tasks.items(), key=lambda kv: kv[1]["first"])
    missing, seen = [], {}
    for task, t in ordered:
        tier = t["tier"] or "untiered"
        earlier = seen.setdefault(tier, [])
        median = statistics.median(earlier) if len(earlier) >= 3 else None
        outlier = median is not None and t["total"] > 2 * median
        earlier.append(t["total"])
        c = {k: sum(u[k] for u in t["usage"].values()) for k in CLASSES}
        line = (f"{task} [{tier}] {human(t['total'])} tokens "
                f"(in {human(c['input'])}, cache read {human(c['cache_read'])}, "
                f"cache write {human(c['cache_write'])}, out {human(c['output'])}); "
                f"active {t['active_s'] // 60} min, wall {t['wall_s'] // 60} min")
        if t["tools"]:
            calls = sum(n for n, _ in t["tools"].values())
            errors = sum(bad for _, bad in t["tools"].values())
            line += f"; {calls} tool calls, {errors} errors"
        if t["checks"]:
            line += "; harness " + ", ".join(f"{name} {bad}/{n} failed"
                                             for name, (n, bad) in sorted(t["checks"].items()))
        if t["budget"]:
            line += f"; budget {human(t['budget'])} ({t['total'] / t['budget']:.1f}x)"
        if task in q:
            first, failed, accepted = q[task]
            line += f"; first result {first}, {failed} failed"
            if accepted:
                hours = (parse_time(accepted) - parse_time(t["first"])).total_seconds() / 3600
                line += f", accepted after {hours:.1f} h"
        if outlier:
            line += f"; OUTLIER (tier median {human(int(median or 0))})"
            line += f"; retro: {t['retro']}" if t["retro"] else "; no retrospective"
            if not t["retro"]:
                missing.append(task)
        print(line)
    for tier, totals in seen.items():
        print(f"tier {tier}: {len(totals)} tasks, median {human(int(statistics.median(totals)))} tokens")
    if args.check and missing:
        for task in missing:
            print(f"E-retro: {task} is over twice its tier median and has no retrospective "
                  f"(`task-meter.py note {task} --retro \"cause; fix: ...\"`)")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Tokens and time per ledger task.")
    parser.add_argument("command", choices=["start", "stop", "note", "report"])
    parser.add_argument("task", nargs="?")
    parser.add_argument("--meter", default="kb/work/meter.jsonl")
    parser.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    parser.add_argument("--tier", choices=["direct", "slice", "full", "defect"])
    parser.add_argument("--budget")
    parser.add_argument("--retro")
    parser.add_argument("--ledger", default="kb/work/ledger.json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--claude-dir", default=str(Path.home() / ".claude" / "projects"))
    parser.add_argument("--codex-dir", default=str(Path.home() / ".codex" / "sessions"))
    args = parser.parse_args()
    meter = Path(args.meter)

    if args.command == "report":
        return report(args)
    if not args.task:
        parser.error(f"{args.command} needs a TASK")
    events = read_events(meter)
    if args.command == "start":
        if open_start(events, args.task):
            print(f"{args.task} is already started; stop it first")
            return 1
        budget = parse_budget(args.budget) if args.budget else None
        if args.budget and budget is None:
            print(f"budget `{args.budget}` is not a token count like 200k or 1.5M")
            return 1
        append(meter, {"event": "start", "task": args.task, "at": now(), "tier": args.tier,
                       "budget": budget, "session": args.session or None, "cwd": os.getcwd()})
        print(f"{args.task} started")
    elif args.command == "stop":
        start = open_start(events, args.task)
        if not start:
            print(f"{args.task} has no open start")
            return 1
        at = now()
        result = measure(args, start, at)
        append(meter, {"event": "stop", "task": args.task, "at": at, **result})
        total = sum(sum(u.values()) for u in result["usage"].values())
        print(f"{args.task} stopped: {human(total)} tokens over {result['requests']} requests, "
              f"active {result['active_s'] // 60} min")
    else:
        if not args.retro:
            parser.error("note needs --retro")
        append(meter, {"event": "note", "task": args.task, "at": now(), "retro": args.retro})
        print(f"{args.task}: retrospective recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
