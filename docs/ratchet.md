# Ratchet result contract

Run `python3 skills/spec-driven-dev/ratchet.py --from-results results.json`
after your test runner completes. Commit `.ratchet.json`: it is the reviewed
high-water mark of passing obligations. Exit 0 means held or advanced; 1 means
failed evidence or regression; 2 means invalid input, state, or I/O failure.

The supported JSON format is:

```json
{
  "version": 1,
  "complete": true,
  "tests": [
    {"id": "citation-renders", "obligation": "P1", "status": "passed"},
    {"id": "hostile-filename", "obligation": "T-3", "status": "passed"}
  ]
}
```

Each test needs a unique, nonempty stable `id`, an obligation matching
`P`, `NF`, or `T` followed by digits (optional hyphen), and a status of
`passed`, `failed`, or `skipped`. Multiple distinct tests may cover one
obligation; **all** must pass for that obligation to qualify. A skipped test
is never passing evidence. Any failed test rejects the run, even for an
obligation not previously recorded. A missing prior obligation is a regression.
An all-skipped report also fails. Empty tests, duplicate test IDs, unknown
statuses, incomplete reports, and invalid or truncated JSON are rejected.

Your runner adapter is a trust boundary: it must report every relevant test,
including failures and skips, with stable IDs. Set `complete: true` only after
the entire intended run finishes normally and its report is complete. Report
runner crashes, collection errors, or an interrupted run as `complete: false`;
do not transform their partial successes into complete evidence. This tool
cannot detect an adapter that omits failures or falsely asserts completeness.
It does not run tests or judge their quality.

Legacy `--from-log`, regex extraction (`--pattern`), and implicit stdin log
input are unsupported. Console output can mention passing IDs in failure
messages, summaries, or unfinished runs. Migrate a runner's structured output
to this JSON contract. `--passing P1,P2,T3` remains an explicitly trusted manual
adapter: supply only obligations independently verified to pass in a complete
run. It does not inspect tests. Empty `--passing` is rejected.

Use `--dry-run` to validate and compare without changing the state. To remove
an obligation deliberately, use `--retire P1 --reason "<at least 20 characters
explaining the approved change>"`. Failed or rejected inputs leave the state
unchanged. Retirement cannot be combined with a result source.

State read/compare/write and retirement are serialized using POSIX `flock` on
`<state>.lock` (Linux supported; Python's `fcntl` is required). A temporary file
in the same directory is flushed and fsynced, then atomically replaces the
state. Concurrent snapshots are evaluated in lock order: an older snapshot
may fail against a newly advanced baseline; retry with complete current results.
Keep the sidecar file in place while processes might run; do not delete or
replace it. Ignore it in version control. Dry runs can create this lock file
but do not alter the JSON state. All writers must use this protocol on a local
filesystem supporting advisory locks and atomic rename. Directory fsync and
power-loss durability guarantees are outside this contract.

Run `sh skills/spec-driven-dev/test-ratchet.sh` for end-to-end checks, including
real concurrent processes and rejection without state changes.
