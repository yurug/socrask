#!/usr/bin/env python3
"""plan-check — the Phase 3 readiness gate of spec-driven-dev.

A step handed to the execution tier must leave that agent nothing to decide:
the cheaper model drifts exactly where the plan left a choice open. This script
checks the shape that makes a step executable without judgment; the format is
in references/execution-ready-steps.md.

Usage:
    plan-check.py [PLAN]

    PLAN   defaults to ./kb/plan.md

Plan shape: one `## Step <n>: <title>` section per step, each with labelled
fields (`Tier: execution`, `**Files:**`, `- Acceptance:` all parse). Field
bodies run until the next label or step heading.

Exit code: 0 = clean (warnings allowed), 1 = errors.

Checks (E = error, W = warning):
    E-missing     the plan file does not exist
    E-no-steps    no `## Step <n>` heading
    E-tier        a step without `Tier: execution` or `Tier: judgment`
    E-field       a step without Acceptance or Proof, or an execution step
                  without Files, Interfaces, Out of scope or Hand off
    E-proof       an execution step whose Proof cites no existing
                  `kb/models/<file>.md#I<n>` invariant, or has no Argument or
                  Refinement; `Proof: none: <reason>` needs a reason
    E-command     an Acceptance item (or the whole field) with no `command`
                  in backticks, so nothing says how the criterion is checked
    E-files       an execution step whose Files field names no `path`
    E-open-choice an execution step that still says TBD/TODO/decide/choose/
                  pick/figure out/as needed/... outside Out of scope and
                  Hand off, where naming a choice is the point
    E-budget      an optional Budget field that is not a token count
                  (`Budget: ~200k tokens`, `1.5M`); task-meter.py compares it
                  with the measured total
    W-steps       more than 4 steps: the slice is probably too large

What this does NOT check: that the proof argument holds, that the settled
choices are right, that a command actually tests its criterion, or that the
execution model can do this class of task. The execution-tier simulation pass
is what finds the questions a well-formed step still leaves open.
"""

import argparse
from pathlib import Path
import re
import sys

STEP_RE = re.compile(r"^##\s+Step\s+(\w+)\b(.*)$", re.IGNORECASE)
LABEL_RE = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?([A-Za-z][A-Za-z ]{1,30}?)(?:\*\*)?\s*:(?:\*\*)?\s*(.*)$")
FIELDS = {
    "tier": "tier",
    "obligations": "obligations",
    "biggest unknown": "unknown",
    "files": "files",
    "interfaces": "interfaces",
    "acceptance": "acceptance",
    "out of scope": "out-of-scope",
    "hand off": "hand-off",
    "proof": "proof",
    "budget": "budget",
    "handoff": "hand-off",
}
EXECUTION_FIELDS = ["files", "interfaces", "out-of-scope", "hand-off"]
# Naming an open choice is legitimate where the step says what it will NOT do,
# when to stop, and what is still unknown; anywhere else it is work left undone.
CHOICE_EXEMPT = {"out-of-scope", "hand-off", "unknown"}
OPEN_CHOICE_RE = re.compile(
    r"\b(TBD|TODO|FIXME|decide|choose|pick|figure out|as needed|if needed|"
    r"as appropriate|somehow|etc\.?|or similar|some kind of)\b", re.IGNORECASE)
CODE_RE = re.compile(r"`[^`]+`")
INVARIANT_RE = re.compile(r"`?(kb/models/[\w./-]+\.md)#(I\d+)`?")
BUDGET_RE = re.compile(r"^~?\s*\d+(?:\.\d+)?\s*[kKmM]?\s*(?:tokens?)?$")
NONE_RE = re.compile(r"^none:\s*(\S.*)", re.IGNORECASE | re.DOTALL)


def parse_steps(text):
    """[(step id, {field: body})], fields keyed by canonical name; unlabelled
    text before the first label lands under 'intro'."""
    steps, current, field = [], None, None
    for line in text.splitlines():
        m = STEP_RE.match(line)
        if m:
            current, field = {"intro": []}, "intro"
            steps.append((m.group(1), current))
            continue
        if current is None:
            continue
        if line.startswith("## "):
            current, field = None, None
            continue
        label = LABEL_RE.match(line)
        name = FIELDS.get(label.group(1).strip().lower()) if label else None
        if label and name:
            field = name
            current.setdefault(field, []).append(label.group(2))
        else:
            current.setdefault(field, []).append(line)
    return [(sid, {k: "\n".join(v).strip() for k, v in body.items()})
            for sid, body in steps]


def acceptance_items(body):
    items = [l for l in body.splitlines() if re.match(r"^\s*[-*\d]", l)]
    return items or [body]


def tier_of(fields):
    # Only the label's own line: prose after it belongs to the step, not the tier.
    return (fields.get("tier", "").splitlines() or [""])[0].strip("`* ").lower()


def check_proof(sid, body, tier, roots):
    """A proof sketch: `none: <reason>`, or (execution tier) an existing
    invariant plus an argument and a refinement map."""
    if not body:
        return [f"E-field: step {sid} has no Proof"]
    if body.lower().startswith("none"):
        m = NONE_RE.match(body)
        if m and len(m.group(1).split()) >= 3:
            return []
        return [f"E-proof: step {sid} says `Proof: none` without a reason "
                "(`Proof: none: <reason>`)"]
    if tier != "execution":
        return []
    errors = []
    cited = INVARIANT_RE.findall(body)
    if not cited:
        errors.append(f"E-proof: execution step {sid} cites no `kb/models/<file>.md#I<n>`")
    for path, inv in cited:
        model = next((r / path for r in roots if (r / path).is_file()), None)
        if model is None:
            errors.append(f"E-proof: step {sid} cites `{path}`, which does not exist")
        elif not re.search(rf"\b{inv}\b", model.read_text(encoding="utf-8")):
            errors.append(f"E-proof: step {sid} cites {inv}, which `{path}` does not declare")
    for label in ("argument", "refinement"):
        if not re.search(rf"^\s*(?:\*\*)?{label}(?:\*\*)?\s*:", body,
                         re.IGNORECASE | re.MULTILINE):
            errors.append(f"E-proof: execution step {sid} has no {label.capitalize()}: "
                          "in its Proof")
    return errors


def check_step(sid, fields, roots):
    errors = []
    tier = tier_of(fields)
    if tier not in ("execution", "judgment"):
        errors.append(f"E-tier: step {sid} has tier `{tier}`, "
                      "expected `execution` or `judgment`")
    if not fields.get("acceptance"):
        errors.append(f"E-field: step {sid} has no Acceptance")
    else:
        for item in acceptance_items(fields["acceptance"]):
            if not CODE_RE.search(item):
                errors.append(f"E-command: step {sid} acceptance `{item.strip()}` "
                              "names no command in backticks")
    errors.extend(check_proof(sid, fields.get("proof", ""), tier, roots))
    budget = fields.get("budget")
    if budget is not None and not BUDGET_RE.match(budget.splitlines()[0].strip() if budget else ""):
        errors.append(f"E-budget: step {sid} budget `{budget}` is not a token count like 200k")
    if tier != "execution":
        return errors
    for name in EXECUTION_FIELDS:
        if not fields.get(name):
            errors.append(f"E-field: execution step {sid} has no {name}")
    if fields.get("files") and not CODE_RE.search(fields["files"]):
        errors.append(f"E-files: execution step {sid} names no `path` under Files")
    for name, body in fields.items():
        if name in CHOICE_EXEMPT:
            continue
        # Code spans are names, not prose: `pick_peer` is not an open choice.
        for m in OPEN_CHOICE_RE.finditer(CODE_RE.sub("", body)):
            errors.append(f"E-open-choice: execution step {sid} ({name}) still says "
                          f"`{m.group(0)}`; settle it in the plan or make the step judgment-tier")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Phase 3 gate: check plan steps are executable.")
    parser.add_argument("plan", nargs="?", default="kb/plan.md")
    args = parser.parse_args()
    plan = Path(args.plan)

    if not plan.is_file():
        print(f"{plan}: E-missing: no plan file")
        return 1
    steps = parse_steps(plan.read_text(encoding="utf-8"))
    if not steps:
        print(f"{plan}: E-no-steps: no `## Step <n>: <title>` heading")
        return 1

    # The plan normally sits in kb/, and model paths are written from the repo root.
    roots = (plan.parent.parent, plan.parent, Path("."))
    errors, warnings = [], []
    for sid, fields in steps:
        errors.extend(check_step(sid, fields, roots))
    if len(steps) > 4:
        warnings.append(f"W-steps: {len(steps)} steps; more than 4 means the slice is "
                        "probably too large")

    for message in errors + warnings:
        print(f"{plan}: {message}")
    n_exec = sum(1 for _, f in steps if tier_of(f) == "execution")
    print(f"{plan}: {len(steps)} steps, {n_exec} execution-tier, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
