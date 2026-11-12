# Findings: [slice or task]

The audit-and-fix ledger of Phase 5. One row per finding; a fix never deletes a row.
`findings-check.py` stops the loop when two rounds in a row find new or reopened high
findings, or when a high finding is still open past the round cap.

| ID | Round | Severity | Finding | Status | Reopened | Evidence |
|---|---|---|---|---|---|---|
| F1 | 1 | [high, medium or low] | [what is wrong, and where] | open | | |

<!-- When the check stops the loop, route the failure with the engineer, then write:
Escalated: round N, forebrief:<card-id> (or the date and the engineer's words) -->
