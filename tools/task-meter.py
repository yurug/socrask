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
                                     TASK must exist in the ledger, when there is one
    task-meter.py stop TASK
    task-meter.py note TASK --retro "cause; fix: <harness or KB change>"
    task-meter.py report [--check] [--ledger kb/work/ledger.json]
    task-meter.py remeasure [TASK]   measure again the unmeasured stops (all, or TASK's),
                                     while the transcripts still exist; rewrites them in place

    --meter        defaults to kb/work/meter.jsonl
    --session      Claude session ID; defaults to $CLAUDE_CODE_SESSION_ID
    --claude-dir   defaults to ~/.claude/projects
    --codex-dir    defaults to ~/.codex/sessions

Attribution: the task's root is the Claude Code session given by --session (or
$CLAUDE_CODE_SESSION_ID), or else the Claude Code session or Codex thread that
ran `task-meter.py start TASK`. The task counts the requests of that root and of
its subagents between the marks, each request once, by runtime, model and role
(the subagent type in Claude Code; the nickname, path or "guardian" in Codex).
A stop that finds no request records the task as unmeasured and exits 1: a
silent zero would read as a free task.

Report, per task: tokens by class, wall-clock and active time (gaps over five
minutes do not count), budget against actual, tool calls and errors, harness
script runs and failures, and from the ledger the first-attempt result and the
number of failed observations. A task whose total is
over twice the median of its tier (three or more earlier tasks) is an outlier.
Two tasks with the same root and overlapping windows share requests; the report
says so. insights.py analyses the whole history.

`report --check` exits 1 when an outlier has no retrospective. It never fails
on cost alone: a budget gate would reward skipping verification.

What this does NOT do: tell useful tokens from wasted ones, split the requests
of two tasks that run at once in one root, or price tokens. A
failed command that runs two harness scripts counts a failure for both.
"""

import argparse
from datetime import datetime, timedelta, timezone
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


def started_here(text, task):
    """Whether a command text starts the meter for this task."""
    return re.search(r"task-meter\.py\s+start\s+" + re.escape(task) + r"(?![\w.-])", text) is not None


def near(at, start):
    """The start command runs a few seconds before the start event it writes."""
    return start - timedelta(minutes=5) <= at <= start + timedelta(minutes=1)


def classes(inp, read, write, out):
    return {"input": inp, "cache_read": read, "cache_write": write, "output": out}


# ---------------------------------------------------------------------------
# Claude Code. A session is one main transcript, <project>/<session>.jsonl, plus
# one transcript per subagent, <project>/<session>/subagents/agent-<id>.jsonl.
# Subagent records carry the parent's sessionId, and a sibling .meta.json names
# the subagent's type, which is its role.

def claude_files(root, since):
    return recent_files(root, "*/*.jsonl", since) + recent_files(root, "*/*/subagents/*.jsonl", since)


def claude_role(path):
    if path.parent.name != "subagents":
        return "main"
    try:
        return json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8")).get("agentType") or "subagent"
    except (OSError, ValueError):
        return "subagent"


def claude_records(path):
    for line in path.open(encoding="utf-8", errors="replace"):
        if '"timestamp"' not in line:
            continue
        try:
            rec = json.loads(line)
            yield rec, parse_time(rec["timestamp"])
        except (ValueError, KeyError, TypeError):
            continue


def claude_find_session(root, start, task):
    """The session that ran `task-meter.py start TASK` around the start time."""
    for path in claude_files(root, start - timedelta(minutes=5)):
        for line in path.open(encoding="utf-8", errors="replace"):
            if task not in line or "task-meter" not in line:
                continue
            try:
                rec = json.loads(line)
                at, content = parse_time(rec["timestamp"]), rec["message"]["content"]
            except (ValueError, KeyError, TypeError):
                continue
            if near(at, start) and isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_use"
                    and started_here(str((b.get("input") or {}).get("command", "")), task) for b in content):
                return rec.get("sessionId")
    return None


def claude_scan(root, start, stop, session):
    """Usage {request: (time, (runtime, model, role), classes)} and tool calls of one
    session and its subagents, between the marks. Each API request counts once."""
    usage, uses, failed = {}, {}, set()
    for path in claude_files(root, start):
        role = claude_role(path)
        for rec, at in claude_records(path):
            if not start <= at <= stop or rec.get("sessionId") != session:
                continue
            msg = rec.get("message") or {}
            u = msg.get("usage")
            if isinstance(u, dict):
                key = rec.get("requestId") or msg.get("id") or f"{path}:{at}"
                usage[key] = (at, ("claude-code", msg.get("model", "unknown"), role), classes(
                    u.get("input_tokens", 0), u.get("cache_read_input_tokens", 0),
                    u.get("cache_creation_input_tokens", 0), u.get("output_tokens", 0)))
            for b in msg.get("content") if isinstance(msg.get("content"), list) else []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    uses[b.get("id")] = (b.get("name", "unknown"), scripts(str((b.get("input") or {}).get("command", ""))))
                elif b.get("type") == "tool_result" and b.get("is_error"):
                    failed.add(b.get("tool_use_id"))
    return usage, [(name, names, key in failed) for key, (name, names) in uses.items()]


# ---------------------------------------------------------------------------
# Codex CLI. Each thread (the user's thread, a spawned subagent, a guardian
# review) writes one rollout file. Its first record, session_meta, gives the
# thread ID, its parent thread and its role; turn_context records give the model.
# The working directory says nothing reliable: a session rooted at the repository
# runs commands in worktrees. So the task's root is the thread that ran the start
# command, and the task's threads are that root and its descendants.

def codex_meta(path):
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            rec = json.loads(f.readline())
    except (OSError, ValueError):
        return None
    p = rec.get("payload") or {}
    if rec.get("type") != "session_meta" or not p.get("id"):
        return None
    spawn = (p.get("source") or {}).get("subagent") if isinstance(p.get("source"), dict) else None
    spawn = spawn.get("thread_spawn") if isinstance(spawn, dict) else None
    if spawn:
        # The role names the job; the path's last part does too; the nickname is random.
        path_role = str(spawn.get("agent_path") or "").rstrip("/").rsplit("/", 1)[-1]
        role = spawn.get("agent_role") or path_role or spawn.get("agent_nickname") or "subagent"
        parent = spawn.get("parent_thread_id") or p.get("parent_thread_id")
    else:
        role = "guardian" if p.get("thread_source") == "guardian_review" else "main"
        parent = p.get("parent_thread_id")
    return {"id": p["id"], "parent": parent, "role": role, "provider": p.get("model_provider")}


def codex_calls(path):
    """(time, payload) of each tool call and tool output in a rollout."""
    for line in path.open(encoding="utf-8", errors="replace"):
        if "_call" not in line:
            continue
        try:
            rec = json.loads(line)
            p, at = rec["payload"], parse_time(rec["timestamp"])
        except (ValueError, KeyError, TypeError):
            continue
        if isinstance(p, dict):
            yield at, p


def codex_find_thread(root, start, task):
    threads = {}
    for path in recent_files(root, "**/*.jsonl", start - timedelta(minutes=5)):
        meta = codex_meta(path)
        if not meta:
            continue
        threads[meta["id"]] = (path, meta)
    for tid, (path, _) in threads.items():
        for at, p in codex_calls(path):
            if p.get("type") in ("function_call", "custom_tool_call") and near(at, start) \
                    and started_here(str(p.get("input") or p.get("arguments") or ""), task):
                return tid, threads
    return None, threads


def codex_scan(root_thread, threads, start, stop):
    """Usage and tool calls of the root thread and its descendants, between the marks."""
    chosen, grew = {root_thread}, True
    while grew:
        grew = False
        for tid, (_, meta) in threads.items():
            if tid not in chosen and meta["parent"] in chosen:
                chosen.add(tid)
                grew = True
    usage, uses, failed = {}, {}, set()
    for tid in chosen:
        path, meta = threads[tid]
        role = "main" if tid == root_thread and meta["role"] == "main" else meta["role"]
        model, records, counts = "unknown", {}, {}
        for n, line in enumerate(path.open(encoding="utf-8", errors="replace")):
            if '"turn_context"' not in line and '"token_usage_record"' not in line and '"token_count"' not in line:
                continue
            try:
                rec = json.loads(line)
                p, at = rec["payload"], parse_time(rec["timestamp"])
            except (ValueError, KeyError, TypeError):
                continue
            if rec.get("type") == "turn_context":
                provider = p.get("model_provider") or meta["provider"]
                model = f"{provider}/{p.get('model')}" if provider and p.get("model") else p.get("model") or model
                continue
            if not start <= at <= stop:
                continue
            # Newer rollouts write a token_usage_record per response and a token_count
            # event for the same response; older ones write only token_count. Keep one.
            if rec.get("type") == "token_usage_record" and isinstance(p.get("usage"), dict):
                records[p.get("response_id") or f"{path}:{n}"] = (at, model, p["usage"])
            elif p.get("type") == "token_count" and isinstance((p.get("info") or {}).get("last_token_usage"), dict):
                counts[f"{path}:{n}"] = (at, model, p["info"]["last_token_usage"])
        for key, (at, m, u) in (records or counts).items():
            cached = u.get("cached_input_tokens", 0)
            usage[key] = (at, ("codex", m, role), classes(
                u.get("input_tokens", 0) - cached, cached, u.get("cache_write_input_tokens", 0),
                u.get("output_tokens", 0)))
        for at, p in codex_calls(path):
            if not start <= at <= stop:
                continue
            key = (tid, p.get("call_id"))
            if p.get("type") in ("function_call", "custom_tool_call"):
                uses[key] = (p.get("name", "unknown"), scripts(str(p.get("input") or p.get("arguments") or "")))
            elif p.get("type") in ("function_call_output", "custom_tool_call_output"):
                out = p.get("output")
                text = " ".join(str(part.get("text", "")) for part in out if isinstance(part, dict)) \
                    if isinstance(out, list) else str(out)
                if any(int(c) != 0 for c in EXIT_RE.findall(text)):
                    failed.add(key)
    return usage, [(name, names, key in failed) for key, (name, names) in uses.items()]


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


def measure(args, start_event, stop_at):
    """Find the task's root (the Claude session given at start, or the session or
    thread that ran the start command), then add up its usage between the marks."""
    start, stop, task = parse_time(start_event["at"]), parse_time(stop_at), start_event["task"]
    claude, codex = Path(args.claude_dir), Path(args.codex_dir)
    usage, calls, root, how = {}, [], None, "none"
    session = start_event.get("session") or claude_find_session(claude, start, task)
    if session:
        usage, calls = claude_scan(claude, start, stop, session)
        root, how = f"claude-code:{session}", "session" if start_event.get("session") else "command"
    else:
        thread, threads = codex_find_thread(codex, start, task)
        if thread:
            usage, calls = codex_scan(thread, threads, start, stop)
            root, how = f"codex:{thread}", "command"
    by_model, agents, times = {}, {}, sorted(at for at, _, _ in usage.values())
    for _, (runtime, model, role), u in usage.values():
        for acc in (by_model.setdefault(model, dict.fromkeys(CLASSES, 0)),
                    agents.setdefault((runtime, model, role), dict.fromkeys(CLASSES + ("requests",), 0))):
            for c in CLASSES:
                acc[c] += u[c]
        agents[(runtime, model, role)]["requests"] += 1
    active = sum(min((b - a).total_seconds(), IDLE_CAP) for a, b in zip(times, times[1:]))
    tools, checks = tally(calls)
    return {"usage": by_model, "requests": len(usage), "tools": tools, "checks": checks,
            "agents": [{"runtime": r, "model": m, "role": role, **acc}
                       for (r, m, role), acc in sorted(agents.items())],
            "root": root, "attribution": how,
            "wall_s": int((stop - start).total_seconds()), "active_s": int(active)}


def open_start(events, task):
    starts = [e for e in events if e["task"] == task and e["event"] in ("start", "stop")]
    return starts[-1] if starts and starts[-1]["event"] == "start" else None


def tasks_summary(events):
    tasks = {}
    for e in events:
        t = tasks.setdefault(e["task"], {"tier": None, "budget": None, "usage": {}, "requests": 0,
                                         "wall_s": 0, "active_s": 0, "first": e["at"], "retro": None,
                                         "spans": 0, "tools": {}, "checks": {}, "agents": [],
                                         "windows": [], "unmeasured": 0, "opened": None})
        if e["event"] == "start":
            t["tier"] = e.get("tier") or t["tier"]
            t["budget"] = e.get("budget") or t["budget"]
            t["opened"] = e["at"]
        elif e["event"] == "stop":
            t["spans"] += 1
            t["unmeasured"] += not e.get("requests")
            t["agents"] += e.get("agents", [])
            if e.get("root") and t["opened"]:
                t["windows"].append((t["opened"], e["at"], e["root"]))
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


def ledger_tasks(ledger):
    """Task IDs of the ledger and its archive, or None when there is no ledger."""
    ledger, ids, found = Path(ledger), set(), False
    for path in (ledger, ledger.with_name(ledger.stem + "-archive.json")):
        try:
            ids |= {t.get("id") for t in json.loads(path.read_text(encoding="utf-8")).get("tasks", [])}
            found = True
        except (OSError, ValueError, AttributeError):
            continue
    return ids if found else None


def quality(ledger):
    """{task: (first result, failed count, first accepted time)} from feedback events."""
    out, feedback = {}, []
    ledger = Path(ledger)
    # The archive beside the ledger (ledger.py archive) holds finished feedback.
    for path in (ledger, ledger.with_name(ledger.stem + "-archive.json")):
        try:
            feedback += json.loads(path.read_text(encoding="utf-8")).get("feedback", [])
        except (OSError, ValueError, AttributeError):
            continue
    for fb in feedback:
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
        if t["unmeasured"]:
            line += f"; UNMEASURED ({t['unmeasured']} of {t['spans']} spans)"
        shared = sorted({other for other, o in tasks.items() if other != task and any(
            r1 == r2 and a1 < b2 and a2 < b1 for a1, b1, r1 in t["windows"] for a2, b2, r2 in o["windows"])})
        if shared:
            line += f"; window shared with {', '.join(shared)}"
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


def remeasure(args, meter):
    """Measure again each stop that found no request, from its own start, and
    rewrite it in place. An earlier version of this tool attributed by working
    directory and wrote zeros; the transcripts may still hold the answer."""
    events, opened, fixed, still = read_events(meter), {}, 0, 0
    for i, e in enumerate(events):
        if e["event"] == "start":
            opened[e["task"]] = e
        elif e["event"] == "stop" and not e.get("requests") and (not args.task or e["task"] == args.task) \
                and e["task"] in opened:
            result = measure(args, opened[e["task"]], e["at"])
            if result["requests"]:
                events[i] = {**e, **result, "remeasured_at": now()}
                fixed += 1
            else:
                still += 1
    meter.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events), encoding="utf-8")
    print(f"remeasure: {fixed} stops measured, {still} still unmeasured")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Tokens and time per ledger task.")
    parser.add_argument("command", choices=["start", "stop", "note", "report", "remeasure"])
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
    if args.command == "remeasure":
        return remeasure(args, meter)
    if not args.task:
        parser.error(f"{args.command} needs a TASK")
    events = read_events(meter)
    if args.command == "start":
        known = ledger_tasks(args.ledger)
        if known is not None and args.task not in known:
            print(f"E-ledger: {args.task} is not a task of {args.ledger}; add it first "
                  "(ledger.py add tasks ...), so that its cost can be joined with its result")
            return 1
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
        if not result["requests"]:
            where = f"in {result['root']}" if result["root"] else "and no session or thread ran the start command"
            print(f"E-unattributed: {args.task} stopped unmeasured: no request found {where}. "
                  "Start the meter from the agent session that does the work.")
            return 1
        total = sum(sum(u.values()) for u in result["usage"].values())
        roles = sorted({a["role"] for a in result["agents"]})
        print(f"{args.task} stopped: {human(total)} tokens over {result['requests']} requests, "
              f"active {result['active_s'] // 60} min, roles {', '.join(roles)}")
    else:
        if not args.retro:
            parser.error("note needs --retro")
        append(meter, {"event": "note", "task": args.task, "at": now(), "retro": args.retro})
        print(f"{args.task}: retrospective recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
