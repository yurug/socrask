#!/bin/sh
# Runs kb-lint.py against every fixture in fixtures/kb-lint/: pass-* must exit 0,
# fail-* must exit 1. Each fixture isolates ONE enforcement-channel defect, so a
# failure here names the check that broke.
#
# --no-git throughout: the fixtures are committed files whose `last-updated`
# stops matching their last commit the moment anything else in the repo moves,
# and W-stale noise is not what these fixtures are about.
set -eu
cd "$(dirname "$0")"

status=0
for dir in fixtures/kb-lint/pass-*; do
  name=$(basename "$dir")
  if out=$(python3 kb-lint.py "$dir/kb" --no-git 2>&1); then
    echo "ok   $name (passed, as expected)"
  else
    echo "FAIL $name -- expected exit 0, got a violation:"
    echo "$out" | sed 's/^/       /'
    status=1
  fi
  # The warning tier is the whole point of this one: a shouted rule outside
  # properties/ is said out loud without failing the build.
  if [ "$name" = "pass-constraint-warns" ] && ! echo "$out" | grep -q "W-unenforced"; then
    echo "FAIL $name -- expected a W-unenforced warning, got none:"
    echo "$out" | sed 's/^/       /'
    status=1
  fi
  # The strongest channels pass, and a proof with no stated boundary still warns.
  if [ "$name" = "pass-structural-proof" ] && ! echo "$out" | grep -q "W-trust"; then
    echo "FAIL $name -- expected a W-trust warning on the boundary-less proof:"
    echo "$out" | sed 's/^/       /'
    status=1
  fi
done

# Each fail-* fixture must fail for ITS OWN reason: exit 1 alone would also be
# satisfied by an unrelated broken link, which would hide a regression.
for dir in fixtures/kb-lint/fail-*; do
  name=$(basename "$dir")
  case "$name" in
    fail-unenforced)      expect="E-unenforced" ;;
    fail-instruction)     expect="E-channel" ;;
    fail-missing-path)    expect="E-channel" ;;
    fail-noreason)        expect="E-noreason" ;;
    fail-table-no-column) expect="E-unenforced" ;;
    fail-nested-properties) expect="E-unenforced" ;;
    *)                 expect="" ;;
  esac
  if out=$(python3 kb-lint.py "$dir/kb" --no-git 2>&1); then
    echo "FAIL $name -- expected a violation, but exit 0:"
    echo "$out" | sed 's/^/       /'
    status=1
  elif [ -n "$expect" ] && ! echo "$out" | grep -q "$expect"; then
    echo "FAIL $name -- failed, but not with $expect:"
    echo "$out" | sed 's/^/       /'
    status=1
  else
    echo "ok   $name (failed with $expect, as expected)"
  fi
done

exit "$status"
