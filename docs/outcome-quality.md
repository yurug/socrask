# User outcome acceptance

Keep code checks and user acceptance separate. A merged change, a running image,
an acknowledgement and a successful user journey are different facts. Start with
a few important journeys; existing unit suites do not need conversion to adopt this gate.

## Feedback to acceptance

For each significant feedback, keep its original request, a stable ID, representative
starting state, expected observable outcome, preservation constraints, owner and case IDs.
Record reproduced, implemented, deployed and accepted independently, with their versions
and evidence. An implementation status never closes acceptance. A repeated complaint
reopens the same outcome, even when its latest cause is a specification gap.

Use the real shape of the failure: scale, existing state, duplicate names, interrupted
work, follow-up turns and device navigation where relevant. Remove private content from
fixtures without simplifying away the structure that triggers the defect. Include a few
meaningful variants and preserve passing journeys. The person reviewing acceptance
starts from the request and resulting state, not the implementer's explanation.

## Gate and contract

`tools/outcome-check.py` is a read-only CLI. Exit 0 means the supplied current report
meets the contract and has no measured rate regression against the supplied baseline;
1 means failed acceptance; 2 means invalid, incomplete or incompatible evidence.
It emits JSON on stdout, never updates a baseline and never deploys anything.

```sh
python3 tools/outcome-check.py --contract quality/contract.json \
  --report quality/candidate.json --baseline quality/previous.json \
  --revision "$EXPECTED_REVISION" --artifact "$EXPECTED_ARTIFACT"
```

Omit `--baseline` only for an explicitly identified initial baseline or reviewed
rebaselining. Caller-supplied expected revision and immutable artifact identity bind the
check to the candidate being promoted. Do not derive them from the report being checked.
The first run establishes a measured baseline; it does not prove improvement.

The version-1 contract has `suite`, reviewed `revision` and a nonempty `cases` array.
Every case is required. Exploratory cases belong in a separate contract/report.

```json
{
  "version": 1, "suite": "core", "revision": "reviewed-v1",
  "cases": [{
    "id": "organize", "fixture": "large-tree-v1", "checker": "identity-v1",
    "feedback": ["F-12"], "min_trials": 5,
    "min_first_pass": 1, "min_final_pass": 1
  }]
}
```

Declare thresholds and trial counts before the candidate runs. Give deterministic
preservation checks a zero-failure policy. For stochastic behavior, choose rates and
repetition counts appropriate to the risk; five successes are an initial observation,
not a statistical guarantee. Keep difficult cases visible instead of weakening their
checker until the candidate passes. Changes to fixtures, checkers, thresholds or scope
need a reviewed contract revision and an explicit baseline transition.

The report has `version: 1`, matching `suite` and `contract_revision`, `complete: true`,
timezone-aware `started_at`/`finished_at`, and:

```json
{
  "subject": {
    "revision": "full-source-revision", "artifact": "sha256:immutable-image",
    "environment": "linux-acceptance", "configuration": "models-prompts-tools-budgets-v1"
  },
  "observed_before": "sha256:immutable-image",
  "observed_after": "sha256:immutable-image",
  "trials": [{
    "case": "organize", "id": "trial-1", "fixture": "large-tree-v1",
    "checker": "identity-v1", "attempts": [{
      "status": "passed", "evidence": ["artifact://result-state-check"],
      "duration_ms": 4500, "cost": 0.03
    }]
  }]
}
```

Include every independent trial and every chronological attempt. Status is `passed`,
`failed`, `skipped` or `unknown`; skips and unknowns prevent acceptance. Evidence references
are required even for failures. Duration and cost include all model/helper/tool calls
for that attempt; cost uses one documented currency across compared reports.
An automatic repair inside the product's ordinary execution belongs to that same attempt;
restarting the user journey is a second attempt. Never replace the first result with it.

The gate requires each case's minimum number of trials, matching fixture/checker versions,
unique trial IDs within each case, and a stable observed artifact from start to finish.
Current evidence expires after 24 hours by default (`--max-age-hours` sets a positive limit).
Missing cases, duplicate JSON keys, malformed numbers, future/reversed times, crashed
runners, stale evidence and incompatible baseline cases are rejected. Baselines must use
the same contract and environment; compared configurations may differ intentionally.

Output reports first-attempt and final success rates, recovered trials, total duration,
total cost, cost per final successful trial and feedback IDs. Baseline rate drops fail
even above the declared floor; improvements are separate from absolute acceptance.
This deliberately conservative comparison is not a significance test: investigate noisy
changes with additional *complete* experiments, keeping all earlier evidence.

## Integration and limits

Register the gate in the actual promotion/announcement command, after running the candidate
in a representative environment and before calling it validated. Run a small post-deploy
smoke on the exact delivered artifact. Provider/model/configuration changes also invalidate
relevant evidence, even when the application image did not change. Daily health checks
are separate from release acceptance and must not stop forever after one report exists.

The gate validates supplied evidence, not its authenticity or the honesty of an adapter.
It cannot know whether a checker tests the right outcome, whether a hidden trial was
discarded, or whether an evidence reference exists. Inspect stored state and delivered
bytes; calibrate qualitative checks against human judgment. The report producer and
promotion wrapper are trust boundaries. A fixture run demonstrates the gate, not product
success. Content-free metrics are preferred; do not ship private transcripts in reports.

Track time to usable result, first-attempt success, regressions and total cost per useful
outcome. Keep a short list of unresolved feedback, with a next action and owner. Human
comprehension checkpoints explain changes; they do not substitute for these observations.
