#!/bin/sh
# The KISS bound, made mechanical.
#
# "If you cannot explain to a new engineer what your harness checks, the harness
# is too complex." That is a rule about a document, so it can be checked like
# one: every checker in this repo must appear in docs/harness.md, and that page
# must stay short enough to read in one sitting. A harness that grows a check
# without growing its inventory is exactly the harness nobody can explain.
#
# The failure mode this guards is real and slow: each check is justified on its
# own, none is ever removed, and one day the team is debugging the harness
# instead of the agent.
set -eu
cd "$(git rev-parse --show-toplevel)"

INVENTORY=docs/harness.md
MAX_LINES=60
status=0

[ -f "$INVENTORY" ] || { echo "harness-inventory: $INVENTORY is missing"; exit 1; }

# Every executable checker, wherever it lives. Test runners and fixtures are not
# checkers -- they exercise the checkers, and listing them would double the page
# without telling anyone what is enforced.
checkers=$(find tools skills -type f \( -name '*.py' -o -name '*.sh' \) \
  ! -name 'test-*' ! -path '*/fixtures/*' ! -name 'ci-local.sh' \
  ! -name 'sync-skills.sh' | sort)

for c in $checkers; do
  if ! grep -qF "$c" "$INVENTORY"; then
    echo "MISSING  $c is a checker but is not listed in $INVENTORY"
    echo "         add one line saying what it refuses, or delete the checker"
    status=1
  fi
done

n=$(wc -l < "$INVENTORY")
if [ "$n" -gt "$MAX_LINES" ]; then
  echo "TOO LONG $INVENTORY is $n lines, over the $MAX_LINES-line budget"
  echo "         the inventory is the harness's own complexity signal: if it no"
  echo "         longer fits, retire checks rather than raising the number"
  status=1
fi

[ "$status" -eq 0 ] && echo "harness-inventory: $(echo "$checkers" | wc -l) checkers, all listed, inventory $n/$MAX_LINES lines"
exit "$status"
