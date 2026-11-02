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
  # Size costs agent context, so an over-long file is said out loud, not failed.
  if [ "$name" = "pass-long-warns" ] && ! echo "$out" | grep -q "W-length"; then
    echo "FAIL $name -- expected a W-length warning, got none:"
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
    fail-method-unenforced) expect="E-unenforced" ;;
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

# Each run lands in an agent's context: many warnings of one code print as one
# line, and --all restores the full list.
tmp=$(mktemp -d)
mkdir -p "$tmp/kb"
printf -- '---\nid: index\ntype: index\nsummary: s\ndomain: d\nlast-updated: 2026-01-01\n---\n# I\n' > "$tmp/kb/INDEX.md"
for n in 1 2 3 4 5; do
  printf -- '---\nid: n%s\ntype: concept\nsummary: s\ndomain: d\nlast-updated: 2026-01-01\n---\n# N\n' "$n" > "$tmp/kb/n$n.md"
done
out=$(python3 kb-lint.py "$tmp/kb" --no-git 2>&1) || status=1
if [ "$(echo "$out" | grep -c W-orphan)" = 1 ] && echo "$out" | grep -q "W-orphan: 5 warnings, first in n1.md, n2.md, n3.md" \
   && [ "$(python3 kb-lint.py "$tmp/kb" --no-git --all | grep -c W-orphan)" = 5 ]; then
  echo "ok   grouped warnings (one line per crowded code, --all lists them)"
else
  echo "FAIL grouped warnings:"
  echo "$out" | sed 's/^/       /'
  status=1
fi
rm -rf "$tmp"

exit "$status"
