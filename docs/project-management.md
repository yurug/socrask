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
Detect prerequisites before dispatch and report blockers immediately through
[the blocker protocol](../skills/spec-driven-dev/references/blockers.md).
The daily review is a follow-up, never a reason to delay asking for a decision.

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

## Blockers

A task with status `blocked` needs a recorded blocker. After resolution it stays
blocked until an explicit resume checks dependencies and WIP.
An open blocker requires that status; split independent work into another task.
Other tasks can omit `blockers`. Project and plan statuses remain aggregates;
record the actionable blockers on their affected tasks.

Each blocker has an `id` unique within the task, `kind` (`decision` or
`dependency`), `status` (`open` or `resolved`), and these fields:

| Field | Meaning |
|---|---|
| `summary` | What prevents the requested outcome, with its impact. |
| `detected_at`, `ref` | Timezone-aware timestamp and local evidence reference. |
| `owner` | The human or team who can provide the decision or dependency. The task owner still owns follow-up. |
| `unblock_when` | The observable condition that permits resumption. |
| `question` | For a decision, the question sent to the responsible human. |
| `options` | For a decision, at least two `{id, action, consequence}` objects with distinct IDs. Include deferral or stopping if only one technical solution exists. |
| `recommended` | For a decision, the recommended option ID. Explain the reason in its consequence or the cited decision record. |
| `resolution` | Required only when resolved: `{at, ref, outcome}`, with a timestamp at or after detection and evidence of the actual result. |

Use the task's `next_action` and `review_on` for follow-up. Keep resolved entries
when resuming work. Cite the human answer for decisions and the observed unblock
condition for dependencies. Choosing to provision access does not prove access
exists: resolve the decision and keep that dependency open until verified.
If the human defers the work, record that decision under the existing feedback
rules. An unresolved failed observation still requires a blocked task and open
feedback; keep its acceptance dependency visible. Deferral is not acceptance.

Example contents of `blocker.json`, passed to `ledger.py block`:

```json
  {
    "id": "B1", "kind": "decision", "status": "open",
    "detected_at": "2026-11-18T10:00:00Z",
    "summary": "Live sync acceptance requires an unavailable test account",
    "ref": "kb/reports/access-check.md", "owner": "project-engineer",
    "unblock_when": "The engineer chooses how to handle live sync acceptance",
    "question": "Provision a test account or defer live sync?",
    "options": [
      {"id": "account", "action": "Provision a scoped test account", "consequence": "Preserves live acceptance; requires owner action"},
      {"id": "defer", "action": "Defer live sync", "consequence": "Reduces this delivery's scope; acceptance stays pending"}
    ],
    "recommended": "account"
  }
```

The cited file must exist. Use the lifecycle commands:

```sh
python3 tools/ledger.py block T-sync @blocker.json
python3 tools/ledger.py resolve T-sync B1 --ref kb/decisions/account.md \
  --outcome="Engineer chose a scoped test account"
# Resolve any remaining access dependency before resuming:
python3 tools/ledger.py resume T-sync --next-action="Run live sync acceptance"
```

Inspect pending choices without changing the ledger:

```sh
python3 tools/ledger.py decisions
python3 tools/ledger.py decisions --owner project-engineer --json
```

The view groups records only when owner, reference, question, options and
recommendation match. It keeps conflicting recommendations separate, shows
transitive affected tasks and due review dates, and lists independent work
candidates under the recorded dependencies and WIP limit. Candidates still need
normal validation before starting. It sends no notifications and makes no decision.

`block` records an open blocker and sets the follow-up action. `resolve` retains
the resolution; `resume` checks every blocker, task dependency and WIP limit.
Use `resume --status reopened` for a task with unresolved failed feedback.
The generic `set` command also refuses blocker deletion or identity changes.
Resolved records are immutable; new evidence creates a new blocker ID.

`project-check.py` reports `open_blockers` and rejects incomplete records or
resumption with an open blocker. With `--history-base`, it also checks blocker
retention and resolutions across commits, including archive-only changes.
A snapshot alone cannot detect direct file edits that delete records. Neither
mode verifies question delivery, alternative quality or human authorship.

Compatibility: existing blocked tasks need these records before the new gate
passes. Use `ledger.py list tasks --status blocked`, then update each with
`ledger.py set`. Do not invent historical detection dates or decisions; record
the current review and cite the available evidence. Old committed snapshots do
not need rewriting. Tasks without blockers keep their existing format.

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
python3 tools/ledger.py block T-S32 @blocker.json
python3 tools/ledger.py add tasks @new-task.json
python3 tools/ledger.py event S32 --result failed --ref kb/reports/s32.md
python3 tools/ledger.py archive
```

Each write validates the ledger with the rules below, and refuses a write that
makes a coherent ledger incoherent. It keeps the file's format, so the diff shows
only the changed lines. `archive` moves closed tasks with finished feedback, and
closed plans and projects with no live child, to `kb/work/ledger-archive.json`.
`project-check.py` reads the archive as part of the ledger.

Archiving records a durable intent before changing either file. If interrupted,
both tools refuse ordinary work until `python3 tools/ledger.py recover` finishes
that intent. Recovery is idempotent and refuses files changed since the intent.
Keep one writing agent per ledger; the journal is crash recovery, not a lock.

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
ledger, its archive and every distinct pair reachable from HEAD but not from the base,
including side branches forked before rollout and changes made by merges. Every
prior feedback ID survives, and its exact event sequence remains a subsequence of
the current sequence. Concurrent events can interleave; dispositions, ownership
and task links can change. Deleting, rewriting or reordering an old event fails.
Blocker identities also survive; a resolved record cannot change. Archive-only
commits participate in the same checks.
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
