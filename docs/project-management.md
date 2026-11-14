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
| Project | `wip_limit`: maximum simultaneous active/reopened tasks across its plans. Its refs explain the intended outcome. Optional `roadmap`: milestones, risks and the engineer's approval, checked by `tools/roadmap-check.py`. A completed milestone names its `architecture_review` and its `retrospective` file. |
| Plan | `project`: owning project ID; refs point to the argued delivery sequence. |
| Task | `plan`, `kind` (`product`, `engineering`, `process`), `depends_on`, `cases`: stable acceptance case IDs; optional `estimate_hours` (agent-hours). |
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

## Iterate

Work runs in iterations: timeboxes of one to two weeks, each with a goal. Each
iteration goes through the same five steps.

1. **Refine the backlog.** Each candidate task has a `priority` (an integer, 1 is
   the highest), a `value` (the outcome it buys, in one sentence), and an
   `estimate_hours`. `ledger.py list tasks --status planned --by-priority` shows
   the backlog in order.
2. **Plan.** Choose the goal and the tasks, from the top of the backlog, within
   the capacity that the history shows: the tasks and hours accepted in the last
   iterations (`insights.py`, section Periods). Record the iteration with
   `ledger.py add iterations @iteration.json`: `project`, `goal`, `start`, `end`,
   `tasks`, and the usual owner, next action, review date and refs. Set it
   `active`. A project runs one active iteration at a time.
3. **Run.** The control loop above, with the daily review.
4. **Review with the engineer.** At the end, show the engineer what was delivered
   against the goal, with the evidence. Record the review as `review: {at, ref}`,
   a forebrief card or the engineer's words.
5. **Look back.** `retro.py draft <iteration> --write`, then the findings and
   their dispositions. Set `retrospective` on the iteration, list the unfinished
   tasks in `carried_over`, and close it.

`project-check.py` checks the shape: a task of an open iteration has a priority
and a value; a task is in one open iteration at most; a closed iteration has its
review, its retrospective, and every unfinished task carried over.

## Read and change it with `ledger.py`

Do not load the ledger into context, and do not write a script to edit it. A
large ledger costs tens of thousands of tokens to read, and a script per change
costs about 1,500 generated characters and can reformat the file. Use the tool:

```sh
python3 tools/ledger.py list tasks --status active --owner me   # one line per entry
python3 tools/ledger.py get T-S32                                # one entry, one line
python3 tools/ledger.py set T-S32 status=blocked next_action="Wait for the owner"
python3 tools/ledger.py add tasks @new-task.json
python3 tools/ledger.py event S32 --result failed --ref kb/reports/s32.md
python3 tools/ledger.py archive
```

Each write validates the ledger with the rules below, and refuses a write that
makes a coherent ledger incoherent. It keeps the file's format, so the diff shows
only the changed lines. `archive` moves closed tasks with finished feedback, and
closed plans and projects with no live child, to `kb/work/ledger-archive.json`.
`project-check.py` reads the archive as part of the ledger.

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

The output is a short JSON receipt. `--pending` adds every unfinished entity;
prefer `ledger.py list`, which filters.

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

## Retain committed observations across revisions

For a Git-backed project, choose one reviewed rollout commit containing the initial
ledger. Keep that full commit ID fixed in the consuming CI configuration and pass it
at every preflight and handoff:

```sh
python3 tools/project-check.py --root . --ledger kb/work/ledger.json \
  --history-base FULL_REVIEWED_COMMIT
```

Vendor both `tools/project-check.py` and `tools/project_history.py`. The selected
ledger path must stay inside the supplied root and cannot traverse a symlink.
The base must be an actual ancestor of the pinned HEAD. The checker reads that
ledger and every distinct ledger state reachable from HEAD but not from the base,
including side branches forked before rollout and changes made by merges. Every
prior feedback ID survives, and its exact event sequence remains a subsequence of
the current sequence. Concurrent events can interleave; dispositions, ownership
and task links can change. Deleting, rewriting or reordering an old event fails.
Old snapshots are checked structurally, without applying today's review deadline
or requiring old reference paths to exist in today's tree.

The receipt reports the fixed base, resolved HEAD, distinct snapshot count and
current ledger digest. Missing objects, an absent/nonancestor base, corrupt ledger
history, shallow repositories and grafts are refused. Git replacement objects and
inherited repository-local environment cannot substitute another history. Fetch
complete history before running CI; do not fall back to the snapshot check on error.

Without `--history-base`, the checker remains usable for non-Git imports and fixtures
but reports `history.checked: false`. A project claiming history retention must
wire the flag into its real launcher and prove refusal with a removed-event fixture.
Do not advance the base to make a failure disappear. Review changes to the pinned
base and checker as control changes, not routine metadata updates.

This preserves committed records within the trusted available Git graph. It does
not authenticate events or recover observations never committed. Two independent
byte-identical JSON events on separate branches lack identities: multiplicity is
preserved within each historical sequence, not as invented global occurrences.
Replacing the trusted repository or checker is outside this control's guarantee.
