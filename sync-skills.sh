#!/bin/sh
# Legacy default is Claude; --target both installs the same reviewed skill for both hosts.
set -eu
exec python3 "$(dirname "$0")/tools/sync-skills.py" "$@"
