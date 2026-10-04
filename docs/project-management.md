# Keep a request accountable until its outcome is observed

A knowledge base explains what a product means. A work ledger tells the team who
must do what next. Keep both: narrative plans explain decisions and tradeoffs;
one versioned ledger supplies operational status. Do not maintain competing status
tables by hand or turn an implementation commit into product acceptance.

## The control loop

1. Capture the original request in an indexed source, with a stable ID. Link that
   ID to a task, its plan and its project. Split compound feedback into explicit
   acceptance cases; a passing half does not close the request.
2. Before starting, name the owner, next action, acceptance cases, dependencies and
   review date. Reserve the worktree/paths using the existing coordination tool.
   The project declares its work-in-progress limit; an exception is a reviewed
   change to that limit, not a task hidden as planned while it is being worked on.
3. Preserve implementation, deployment and observed acceptance as distinct evidence.
   The implementer supplies a source revision; delivery supplies its immutable
   artifact; acceptance identifies that same revision/artifact and every case.
4. A repeated failure reopens the same task. Keep the previous evidence and add the
   new report. Acceptance predating that report cannot close it again.
5. At handoff and each working day, review active work, blocked work, overdue reviews,
   imported uncertainty and work awaiting release/acceptance. Change the next action
   after doing the review; moving a date alone is not evidence of progress.

Unresolved failed observations require open feedback and a reopened or explicitly
blocked task; blocked work keeps its owner and next action without consuming WIP.

The integration owner owns reconciliation across documents and branches. A worker
reports its exact tested source and limits; it does not close the whole journey.
The owner of a blocked task still owns getting its dependency or decision resolved.

## One small ledger

Store `kb/work/ledger.json` in the consuming project. Version 1 has `sources`,
`projects`, `plans`, `tasks` and `feedback` arrays. Each entity has `id`, `status`,
`owner`, `next_action`, `review_on` and nonempty `refs` to local evidence/spec files.
References may carry a Markdown fragment; the checker verifies the file, not its
fragment. References cannot escape the repository. Dates use ISO `YYYY-MM-DD`;
evidence events use timezone-aware timestamps.

| Entity | Additional fields and meaning |
|---|---|
| Source | `path`, `id_pattern`: one regex capture group extracts the commitment IDs that must be covered. Use the original request/backlog table, not a list generated from the ledger itself. |
| Project | `wip_limit`: maximum simultaneous active/reopened tasks across its plans. Its refs explain the intended outcome. |
| Plan | `project`: owning project ID; refs point to the argued delivery sequence. |
| Task | `plan`, `kind` (`product`, `engineering`, `process`), `depends_on`, `cases`: stable acceptance case IDs. |
| Feedback | `task`, `events`: retained observations `{at, result, ref}`, where result is `failed` or `accepted`. This also covers backlog commitments. |

Project/plan/task statuses are `planned`, `active`, `blocked`, `deferred`,
`imported-unverified`, `closed`; tasks also allow `reopened`. Feedback is `open`,
`deferred`, `imported-unverified`, `accepted`, `rejected` or `waived`. Rejected/waived
feedback needs `disposition: {rationale, ref}` identifying the actual scope decision.
Silence is not a waiver. A project or plan cannot close with unfinished children.

An `imported-unverified` row needs a `migration_note`, owner, next action and review
date. It preserves an existing claim without endorsing it. A product task can omit
case IDs only in this state, while the owner refines the contract. Report this debt
prominently; importing every row is not accepting every outcome.

Example of a reopened task (the named files must exist in the consuming project):

```json
{
  "id": "T-S32", "plan": "PL-INTERACTION", "kind": "product",
  "status": "reopened", "owner": "integration-owner",
  "next_action": "Reproduce the reported gesture from ordinary empty explorer space",
  "review_on": "2026-10-05", "refs": ["kb/spec/drive-explorer.md"],
  "depends_on": [], "cases": ["empty-canvas", "grid", "list", "preservation"]
}
```

For a closed product task, `closure` contains three records:

```json
{
  "implementation": {"revision": "FULL_GIT_HASH", "at": "TIMESTAMP", "ref": "PATH"},
  "deployment": {"revision": "SAME_HASH", "artifact": "sha256:DIGEST", "at": "TIMESTAMP", "ref": "PATH"},
  "acceptance": {
    "revision": "SAME_HASH", "artifact": "sha256:SAME_DIGEST", "at": "TIMESTAMP",
    "environment": "representative-browser", "ref": "PATH",
    "cases": [{"id": "empty-canvas", "status": "passed", "ref": "PATH"}]
  }
}
```

This shape is illustrative, not a valid report: replace placeholders and supply
every case. Nonproduct closure uses `{at, ref}` identifying its executed result;
accepted feedback then cites that executed completion and a newer acceptance event.
Do not relabel a product change to evade delivery evidence. Detailed product
evidence remains governed by [outcome acceptance](outcome-quality.md).

## Make omission and false closure fail

Run the read-only checker from the kit checkout, or vendor the exact file with its
revision and hash recorded:

```sh
python3 tools/project-check.py --root . --ledger kb/work/ledger.json
```

Register this command in the real CI preflight and handoff command. Test the real
launcher with a valid registry and a deliberately orphaned request; a documented
command that the runner skips is not adoption. The kit runs its validator tests
through `tools/ci-local.sh`. The consuming project owns its source adapters and
checks that all input channels are represented, including newly received feedback.

Exit 0 means the supplied work record is coherent, not that the product works.
Exit 2 rejects malformed or inconsistent input: uncovered IDs, missing ownership,
broken references, expired reviews, dependency cycles, premature starts, WIP excess
and unsupported closure. Closed history does not become overdue. `--as-of` exists
for deterministic historical tests; routine CI must use the actual date.

## What still requires judgment

The checker cannot discover feedback never captured in a declared source, certify
the truth of evidence, judge whether a scenario represents the complaint, or prove
that an owner performed a review. It does not run acceptance tests. A regex adapter
can be dishonest; review source selection and keep an omission regression test.
The closure receipt verifies version consistency, not per-request serving identity:
acceptance runners must establish that binding, including mixed replicas/restarts.

Start adoption by reconciling existing commitments into explicit unknowns. Resolve
the oldest reopened and blocked outcomes before expanding work. Keep dates and
owners visible, preserve original reports, and never present the size of the KB,
number of tests, or publication of this method as evidence of product improvement.
