#!/bin/sh
# SessionStart hook: emit personal context from the sidecar.
set -eu
exec python3 -c '
import json, pathlib, sys
profile = pathlib.Path(sys.argv[1]) / "PROFILE.md"
if profile.is_file():
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": profile.read_text()}}))
' "${1:?usage: inject-profile.sh SIDECAR_DIR}"
