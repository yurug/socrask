# Turn blockers into decisions and next actions

Detect blockers before dependent work starts. When the agent cannot resolve one
within its mandate, the coordinator asks the responsible human with options and
a recommendation. A worker's failure report starts that conversation; it does
not end the team's responsibility.

## Detect and route

At intake, before planning or dispatch, and when new evidence invalidates an
assumption, check the requested outcome's prerequisites. Check access, external
capabilities, dependencies, acceptance evidence and unsettled scope or authority.
Test the prerequisite most likely to invalidate downstream work first. Use a
bounded probe when evidence is missing; do not turn preparation into an exhaustive audit.

| Finding | Next action |
|---|---|
| Ordinary failure within the agreed contract | Repair or investigate within the existing retry budget. No new permission request. |
| Uncertain feasibility | Run the cheapest bounded probe. State the uncertainty; one failed attempt does not prove impossibility. |
| Dependency outside the agent's control | Name its owner, the unblock condition and the next review. Escalate if a human must choose a workaround or change scope. |
| Incompatible requirements, unavailable capability, or choice outside the mandate | Ask the responsible human immediately with evidence, options and a recommendation. |

Do not spend the two-attempt or seven-iteration budget on a known human decision.
Do not ask again when an existing decision or authorization already settles it.
If X cannot work under the current constraints, say which constraint fails and
offer feasible alternatives, including a scope change or explicit deferral.
Never silently substitute an easier outcome or invent options that cannot work.

## One conversation, as soon as the blocker is known

A worker sends the coordinator the affected task IDs, evidence, impact, options
and suggested next action as soon as it finds the blocker. Do not wait for the
final report, all workers, the next daily review or the retry cap. The coordinator
checks existing decisions, consolidates duplicates and forwards the unresolved
choice to the responsible human. It must not merely collect the worker's report.
For a solo agent, the same agent owns both roles.

Use an asynchronous question when available and continue independent work.
With Forebrief enabled, use its existing decision routing and share the pending
card promptly. Otherwise ask in the current conversation and retain the answer
in the KB. Do not make installing a decision tool a prerequisite to reporting a blocker.

Keep the request short and actionable:

```text
B1 — Decision needed: live sync requires access that this agent lacks.
Evidence: <failed access check or capability constraint>; blocks T-sync and T-release.
A (recommended): provide a scoped test account; preserves live acceptance, needs owner action.
B: defer live sync; other work can ship only under an explicitly revised scope.
Please choose A or B, or specify another acceptable outcome.
While waiting: continue T-parser; live acceptance remains pending.
Needed before: <dependent step or real deadline>; owner: <responsible human>.
```

Explain recommendation and consequences, including cost, delay or reduced scope
where material. If only one technical solution exists, compare it with deferring
or stopping the affected work. The human can supply another answer.
Do not fabricate urgency. An unanswered request stays pending: elapsed time and
a proposed default are not consent. Remind on the agreed review date or when
impact changes, not on every agent turn.

## Track, continue, resume

Use the task's `blockers` entries in the existing work ledger; see
[the record contract](../../../docs/project-management.md#blockers).
The task owner remains accountable; the blocker owner is the person or team who
can supply the decision or dependency. Keep `next_action` and `review_on` concrete.
Link shared blockers to one decision record so the coordinator asks only once.
`ledger.py decisions` groups pending choices and shows independent work candidates.
After an interruption, read the retained decision state and handoff before asking
again. A pending answer stays pending; a recorded authorization remains usable
within its scope. Recheck any prerequisite that may have changed.
Without a ledger yet, keep the same facts in the plan or session handoff and ask
immediately; bootstrap must not delay escalation.

Mark only the affected tasks `blocked`. Split independent work into separate
tasks and continue it within existing scope and WIP limits. Do not start work
whose validity depends on a particular answer, even under a hidden default.
Keep worktree claims or explicitly hand them off; a blocked task does not release
paths. If nothing independent remains, send the decision request and a resumable
handoff naming the exact condition for continuation. Do not claim completion.

On an answer, record the actual decision and update the plan, assumptions and
acceptance criteria it changes. Check whether the unblock condition now holds:
permission to request access is not access. Keep any remaining dependency open.
Use `ledger.py block`, `resolve` and `resume` for these transitions. Resolved
records remain immutable; a new blocker gets a new ID. Resolve each satisfied
blocker with evidence, then resume its tasks. Revalidate
dependent work; resolving a blocker does not itself satisfy task acceptance.

## Verification boundary

`ledger.py` refuses deleted blockers; `project-check.py --history-base` also
checks retention across commits and archives. The snapshot gate rejects incomplete
records and resumption with open blockers. It cannot detect unreported blockers, deliver questions, authenticate
human answers or judge whether options are useful. Review real team transcripts
for detection timing, prompt escalation and continued independent work. Passing
record checks alone does not establish those behavioral outcomes. Use the
[synthetic agent scenarios](../../../docs/agent-evaluation.md) for repeatable probes.
