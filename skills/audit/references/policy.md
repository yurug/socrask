# One policy for audits and repairs

This policy governs the audit skill and Phase 5 of spec-driven development.
The user's scope and authorization determine the mode; the word "audit" alone
does not authorize repairs.

| Mode | Work | Completion |
|---|---|---|
| Review | Inspect, run relevant checks, reproduce and challenge findings. Preserve product files. | Deliver prioritized findings, evidence and limits. A green suite is not a reason to stop investigating a stated failure. |
| Repair | Review, then repair verified defects within the authorized scope and add regression checks. | Re-audit the result and report remaining defects honestly. |

## Repair rounds

A round is one audit of the current artifact followed by its authorized fixes.
Record findings and their dispositions in the same findings ledger throughout
the repair: `templates/kb/reports/findings.md` supplies the shape.

- The default budget is **three audit rounds**, including the first audit.
  Record `Audit round: N` after every audit, even with no new findings.
- From round two, a new or reopened high finding counts as a strike. Two
  consecutive strikes require arbitration before further fixes.
- An open high finding at the round cap also requires arbitration. Do not mark
  it resolved or start a new ledger to reset the budget.
- `findings-check.py LEDGER` enforces these rules. A different cap requires an
  explicit `Round budget: N, <decision>` in the ledger and the same `--max-rounds`
  value in the real launcher. A fresh agent inherits the existing round count.
- A decision outside the agent's mandate goes to the coordinator immediately;
  do not wait for the cap. Report evidence, options and a recommendation.
- Review mode does not enter this repair loop. A later request to fix the
  findings uses that initial review as round one.

The seven implementation attempts in Phase 4 belong to implementation of a step.
They do not grant extra audit rounds. Re-running a test after a bounded repair
does not itself create another audit round.

## Evidence and acceptance

Retain only findings that affect correctness or a stated requirement. For each,
record what was demonstrated, what could refute it, and what remains uncertain.
Reproduce consequential findings against the original contract before fixing
them. A documented limitation can justify a proposed improvement; label it as
such rather than presenting it as an undisclosed guarantee.

A repair is complete when its regression check and the affected acceptance
checks pass, and the final review has no unresolved critical or high defect.
If the budget ends first, report the unfinished work and request arbitration.
Lower-severity deferrals keep an owner and next action. Never convert a pending
human decision, missing validation or expired budget into a success claim.
