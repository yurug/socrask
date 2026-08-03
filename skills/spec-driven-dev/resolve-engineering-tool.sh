#!/bin/sh
# Resolve an engineer-engineering tool even when an agent host inherited a
# reduced PATH. Print one executable path, or exit 1 without output.
set -eu

tool=${1:-}
case "$tool" in
  inbrief|forebrief|backbrief) ;;
  *) exit 2 ;;
esac

found=$(command -v "$tool" 2>/dev/null || true)
if [ -n "$found" ] && [ -x "$found" ]; then
  printf '%s\n' "$found"
  exit 0
fi

npm_prefix=$(npm prefix -g 2>/dev/null || true)
for candidate in \
  "${npm_prefix:+$npm_prefix/bin/$tool}" \
  "$HOME/.npm-global/bin/$tool" \
  "$HOME/.local/bin/$tool" \
  "$HOME/work/dev/$tool/packages/cli/dist/bin/$tool.js"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    printf '%s\n' "$candidate"
    exit 0
  fi
done

exit 1
