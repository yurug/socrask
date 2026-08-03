#!/bin/sh
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
resolver="$here/resolve-engineering-tool.sh"

fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
mkdir -p "$fixture/.npm-global/bin"
touch "$fixture/.npm-global/bin/inbrief"
chmod +x "$fixture/.npm-global/bin/inbrief"

resolved=$(env -i HOME="$fixture" PATH=/usr/bin:/bin "$resolver" inbrief)
[ "$resolved" = "$fixture/.npm-global/bin/inbrief" ]

if "$resolver" unknown >/dev/null 2>&1; then
  echo "unknown tool unexpectedly resolved" >&2
  exit 1
fi

echo "resolve-engineering-tool: ok"
