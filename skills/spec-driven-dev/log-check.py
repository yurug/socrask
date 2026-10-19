#!/usr/bin/env python3
"""log-check — no secret in a log call.

Observability logs structured events at component boundaries; a log that
carries a credential publishes it to every reader of the logs. This check
works across languages: it flags a log call whose line names a value that
looks like a secret.

Usage:
    log-check.py [PATH...] [--exclude GLOB]...   PATH defaults to the current directory

Exit code: 0 = clean, 1 = errors.

Checks:
    E-secret-log  a log call on a line that names a secret-like identifier
                  (password, secret, api key, private key, access/auth/refresh
                  token, credential, bearer)

Suppress a false positive on the same or the previous line with
`log-check: ok <reason of three words or more>`.

What this does NOT check: a secret held in a variable with a neutral name,
personal data, or what a log library adds on its own. Review covers those.
"""

import argparse
import fnmatch
from pathlib import Path
import re
import sys

EXTENSIONS = {".py", ".ml", ".mli", ".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".go",
              ".java", ".kt", ".scala", ".c", ".h", ".cc", ".cpp", ".rb", ".php", ".sh", ".ex",
              ".exs", ".swift", ".cs"}
SKIP_DIRS = {".git", "node_modules", "_build", "_opam", "target", "dist", "build", "vendor",
             ".venv", "venv", "__pycache__", "fixtures"}
LOG_RE = re.compile(
    r"\b(?:log(?:ger)?|logging|console|tracing|slog|zap|syslog|Logs?)\s*(?:\.|::)\s*"
    r"(?:debug|info|warn(?:ing)?|error|err|fatal|critical|trace|log|msg|app|exception)\b"
    r"|\b(?:debug|info|warn|error|trace)!\s*\(", re.IGNORECASE)
SECRET_RE = re.compile(
    r"(?:password|passwd|secret|api_?key|private_?key|(?:access|auth|refresh|id|api|bearer)_?token"
    r"|credential|bearer)", re.IGNORECASE)
SUPPRESS_RE = re.compile(r"log-check:\s*ok\s+(\S+\s+){2,}\S*")


def files(paths, exclude=()):
    for root in paths:
        root = Path(root)
        if root.is_file():
            yield root
            continue
        for path in root.rglob("*"):
            if path.suffix in EXTENSIONS and path.is_file() and \
                    not SKIP_DIRS.intersection(path.relative_to(root).parts[:-1]) and \
                    not any(fnmatch.fnmatch(path.name, g) for g in exclude):
                yield path


def main():
    parser = argparse.ArgumentParser(description="Refuse secrets in log calls.")
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--exclude", action="append", default=[],
                        help="file-name glob to skip, e.g. 'test-*'")
    args = parser.parse_args()
    errors, scanned = [], 0
    for path in files(args.paths, args.exclude):
        scanned += 1
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for n, line in enumerate(lines):
            if not LOG_RE.search(line):
                continue
            m = SECRET_RE.search(line)
            if not m:
                continue
            if SUPPRESS_RE.search(line) or (n and SUPPRESS_RE.search(lines[n - 1])):
                continue
            errors.append(f"{path}:{n + 1}: E-secret-log: log call names `{m.group(0)}`; "
                          "log an identifier or a redacted marker instead")
    for e in errors:
        print(e)
    print(f"log-check: {scanned} files, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
