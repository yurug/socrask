#!/bin/sh
# Stop hook: ask the visual question once per session, at the end of a turn.
#
# WHY THIS EVENT AND THIS OUTPUT SHAPE — measured, three failures deep:
#   1. PreToolUse on the artifact tool, emitting hookSpecificOutput.additionalContext:
#      the script demonstrably RAN (side-effect probe, after a full session restart)
#      and the text never reached the model. Twice.
#   2. PostToolUse, same field: also ran, also never delivered.
#   3. A Stop hook exiting 0 with plain stdout: same class of silence.
#      The docs list additionalContext as supported on all three. This build does
#      not deliver it on any of them.
# What DOES reach the model, verified by reading the one hook in this setup that is
# observed working (the laconic plugin's own stop-check) and by this hook firing:
# `{"decision": "block", "reason": "..."}` on stdout, exit 0.
#
# "block" here means the turn does not end yet and the model must answer — it does
# NOT block the artifact, which has already shipped. That is exactly the decided
# policy: a missing visual asks once, and a one-line reason is an acceptable answer.
# A per-session marker keeps it to once, so it can never nag; and it stands down
# entirely when a stop hook is already what is driving the turn, so blocks never stack.
set -eu

INPUT=$(cat 2>/dev/null || printf '{}')
read -r STOP_ACTIVE SESSION_ID <<EOF
$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(int(bool(d.get("stop_hook_active"))), d.get("session_id") or "nosession")
' 2>/dev/null || printf '0 nosession')
EOF

# Already continuing because of a stop hook: never stack another block.
[ "$STOP_ACTIVE" = "1" ] && exit 0

root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# The checker ships NEXT TO THIS SCRIPT, not in the repo being checked: a consumer
# repo installs this hook by absolute path and has no tools/ of the kit's own.
# Resolving it from $root silently no-op'd in every repo but the kit — found by
# running it in a sibling and not believing the silence.
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
check="$script_dir/visual-check.py"
[ -x "$check" ] || exit 0

marker="${TMPDIR:-/tmp}/.visual-asked-${SESSION_ID}"
[ -e "$marker" ] && exit 0

# Only artifact directories that exist in THIS repo — no machine-specific paths.
dirs=""
for d in kb/reports reports research methodology; do
  [ -d "$root/$d" ] && dirs="$dirs $root/$d"
done
[ -n "$dirs" ] || exit 0

# shellcheck disable=SC2086
findings=$(python3 "$check" $dirs 2>/dev/null | grep -E '^(ERROR|WARN)' || true)
[ -n "$findings" ] || exit 0

: > "$marker" 2>/dev/null || true
python3 - "$findings" <<'PY'
import json, sys
reason = (
    "Visual check on this repo's artifacts:\n\n" + sys.argv[1] + "\n\n"
    "An ERROR is a hand-drawn visual with no \"unvalidated visual\" marker — fix it.\n"
    "A WARN is an artifact of a diagrammable genre carrying no visual: either add "
    "one (the `primitives` skill; a stepped sequence of stills beats an animation) "
    "or say in one line why prose is better there. Both answers are fine — silence "
    "is not. Asked once per session."
)
print(json.dumps({"decision": "block", "reason": reason}))
PY
exit 0
