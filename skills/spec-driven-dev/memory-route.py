#!/usr/bin/env python3
"""memory-route — a project rule saved to agent memory is routed to the KB.

Claude Code's auto-memory pulls the engineer's guidance into a per-machine,
unversioned directory that other agents and engineers never see. In a
spec-driven project, a rule about the project belongs in the KB. This
PostToolUse hook runs after a Write or Edit. When the file is a `feedback` or
`project` memory and the working directory holds a KB, it asks the agent to
move the rule to `kb/conventions/method.md`.

Usage (hook, JSON on stdin): memory-route.py
Template: templates/settings/memory-route.settings.json

Exit code: always 0; the hook informs the agent and never blocks.

What this does NOT check: whether the agent moved the rule, or a rule kept in a
`user` memory. kb-lint holds the moved rule to its channel.
"""

import json
from pathlib import Path
import re
import sys

ROUTED = re.compile(r"^\s*type:\s*(feedback|project)\b", re.MULTILINE)


def kb_root(cwd):
    return next((d for d in (cwd, *cwd.parents) if (d / "kb" / "INDEX.md").is_file()), None)


def main():
    try:
        event = json.load(sys.stdin)
        target = Path(event["tool_input"]["file_path"])
        cwd = Path(event.get("cwd") or ".")
    except (ValueError, KeyError, TypeError):
        return 0
    if "memory" not in target.parts or ".claude" not in target.parts or target.name == "MEMORY.md":
        return 0
    root = kb_root(cwd)
    match = ROUTED.search(target.read_text(encoding="utf-8")) if target.is_file() else None
    if root is None or match is None:
        return 0
    message = (f"You saved a `{match.group(1)}` memory in a spec-driven project ({root}). "
               "Agent memory is per machine; other agents and engineers never read it. "
               "If it states a rule about this project, on code or method, write it in the "
               "same commit as a rule `M<n>` in `kb/conventions/method.md`, with `Origin:` "
               "and `Enforced-by:`. Then keep the memory only as a pointer to that rule, or "
               "delete it. A preference about the person stays in memory.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                             "additionalContext": message}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
