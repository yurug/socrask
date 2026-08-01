# Backbrief command-line reference

Backbrief opens a grounded comprehension session after a change. The agent builds a cited
map of what changed; only the engineer can advance understanding in the browser.

After installing the public engineer-engineering toolsuite, invoke commands as
`backbrief …`.

| Command | Does |
|---|---|
| `backbrief serve [--repo DIR] [--focus diff:FROM..TO\|component:PATH\|system] [--title T] [--port N] [--open]` | Starts a local session and prints its URL, tokens, port, session id, and PID. |
| `backbrief act FILE.json` / `backbrief act -` | Posts an agent-authored map action, answer, finding, or KB proposal and prints citation validation. |
| `backbrief events [--since N] [--follow] [--timeout SECS]` | Streams the human's annotations, responses, and findings as JSONL. |
| `backbrief status` | Reports the session state, URL, and whether agent and human have engaged. |
| `backbrief digest` | Prints cross-session coverage, open questions and findings, and recently understood ground. |
| `backbrief stop` | Ends the session and flushes its digest without inventing human understanding. |

Exit `0` from `act` means every citation validated. Exit `2` means the action was posted
with one or more citations visibly flagged as unverified; repair the citation rather than
treating it as grounded. Exit `1` is a malformed action, missing server, or transport error.

## Scope the checkpoint

- Use `diff:FROM..TO` for the normal per-cycle checkpoint.
- Use `component:PATH` when onboarding an engineer onto one subsystem.
- Use `system` only for a genuinely small repository.

Read `backbrief digest` before resuming a repository. Revisit invalidated citations first,
then the current frontier. Run `events --follow` while the browser session is active; if the
runtime only yields background output when a process exits, use
`backbrief events --follow --timeout 20` repeatedly.

Backbrief runtime files and credentials live under `.backbrief/` and must remain ignored.
The server binds to `127.0.0.1`. Never post `got-it`, mastery, or another human-only action
from the agent credential.
