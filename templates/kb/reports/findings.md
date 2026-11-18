# Findings: [slice or task]

The audit-and-fix ledger of Phase 5. One row per finding; a fix never deletes a row.
`findings-check.py` stops the loop when two rounds in a row find new or reopened high
findings, or when a high finding is still open at the round cap.

Audit round: 1

Increment after each audit, including one with no new findings.

| ID | Round | Severity | Finding | Status | Reopened | Evidence |
|---|---|---|---|---|---|---|
| F1 | 1 | [critical, high, medium or low] | [what is wrong, and where] | open | | |

<!-- When the check stops the loop, route the failure with the engineer, then write:
Escalated: round N, forebrief:<card-id> (or the date and the engineer's words) -->

For a nondefault cap, record `Round budget: N, <engineer decision>` and pass
the same `--max-rounds N` to the checker.
