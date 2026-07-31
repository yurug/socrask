#!/bin/sh
# Runs kb-lint-forebrief.py against every fixture pair in
# fixtures/forebrief-lint/: pass-* must exit 0, fail-* must exit 1.
# Invoked directly, or as forebrief's own tools/ci-local.sh's last step
# (kb/conventions/testing-strategy.md: "forebrief's CI runs them").
set -eu
cd "$(dirname "$0")"

status=0
for dir in fixtures/forebrief-lint/pass-*; do
  name=$(basename "$dir")
  if out=$(python3 kb-lint-forebrief.py "$dir/kb" 2>&1); then
    echo "ok   $name (passed, as expected)"
  else
    echo "FAIL $name -- expected exit 0, got a violation:"
    echo "$out" | sed 's/^/       /'
    status=1
  fi
  if [ "$name" = "pass-routing-tripwire" ] && ! echo "$out" | grep -q "W-routing"; then
    echo "FAIL $name -- expected a W-routing warning, got none:"
    echo "$out" | sed 's/^/       /'
    status=1
  fi
done

for dir in fixtures/forebrief-lint/fail-*; do
  name=$(basename "$dir")
  if out=$(python3 kb-lint-forebrief.py "$dir/kb" 2>&1); then
    echo "FAIL $name -- expected a violation, but exit 0:"
    echo "$out" | sed 's/^/       /'
    status=1
  else
    echo "ok   $name (failed, as expected)"
  fi
done

exit "$status"
