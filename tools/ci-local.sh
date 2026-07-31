#!/bin/sh
# Everything in this repo that has an exit code, in one command.
#
# WHY THIS EXISTS: the kit tells projects that a rule which matters gets a
# deterministic check, and until now its own checks ran only when someone
# remembered them. A test suite nobody runs is the instruction tier wearing a
# test suite's clothes.
#
#   tools/ci-local.sh
#
# Wire it into commits (the hook is not versioned, so this is opt-in per clone):
#   ln -sf ../../tools/ci-local.sh .git/hooks/pre-commit
set -eu
cd "$(git rev-parse --show-toplevel)"

status=0
run() {
  echo "== $1"
  shift
  if "$@"; then :; else
    echo "-- FAILED: $*"
    status=1
  fi
}

run "kb-lint fixtures (enforcement channels)" ./skills/spec-driven-dev/test-kb-lint.sh
run "forebrief-lint fixtures (verbatim rationale)" ./skills/spec-driven-dev/test-kb-lint-forebrief.sh
run "visual honesty gate" python3 skills/primitives/visual-check.py
run "skill metadata and shipped references" python3 tools/skill-check.py

# forebrief's NF1 ("the forebrief skill file stays <= 120 lines") is a budget on
# a file THIS repo owns, so this is the only place it can be checked at all.
# forebrief's KB declares NF1 as `none:` pointing here, and that reason is only
# honest while this step exists.
skill_budget() {
  n=$(wc -l < skills/forebrief/SKILL.md)
  if [ "$n" -le 120 ]; then
    echo "skills/forebrief/SKILL.md: $n/120 lines"
  else
    echo "skills/forebrief/SKILL.md is $n lines, over the 120-line budget (forebrief NF1)"
    echo "-- growth past the budget is a protocol-too-wide smell, not a docs problem"
    return 1
  fi
}
run "forebrief skill line budget (NF1)" skill_budget

persistent_context_budget() {
  n=$(wc -l < templates/claude-md/spec-driven.md)
  if [ "$n" -le 120 ]; then
    echo "templates/claude-md/spec-driven.md: $n/120 lines"
  else
    echo "templates/claude-md/spec-driven.md is $n lines, over the 120-line persistent-context budget"
    return 1
  fi
}
run "persistent context line budget" persistent_context_budget
run "ratchet (what passed stays passed)" ./skills/spec-driven-dev/test-ratchet.sh
run "harness inventory (the KISS bound)" tools/harness-inventory.sh

# Not run here: kb-lint against templates/kb. That template is meant to fail on
# its own `YYYY-MM-DD` and `<type>` placeholders — that is what makes a fresh
# copy tell you what to fill in — so its exit code carries no signal.

if [ "$status" -eq 0 ]; then
  echo "== all green"
else
  echo "== FAILURES above"
fi
exit "$status"
