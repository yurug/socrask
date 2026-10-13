# Execution-ready plan steps

A cheaper execution model fails where the plan leaves a choice open: it makes
the choice, makes it differently from the planner, and the loop spends its
iterations on a disagreement nobody wrote down. The fix is in the plan, not in
the executor. Every choice gets settled on the judgment tier, in `kb/plan.md`,
before the step is handed off.

## Tier per step

Each step declares `Tier: execution` or `Tier: judgment`.

- **judgment**: unfamiliar integration, acceptance design, consequential repair,
  or any step whose content is a choice. Runs on the session model.
- **execution**: everything the step needs is already decided. It runs on an
  execution model that has been validated for this task class (Model routing
  rule 3). A well-formed step does not replace that validation.

If a step mixes the two, split it: the judgment step comes first and writes its
decision into the KB, then the execution step cites that decision.

## Step format

```markdown
## Step 1: <observable result>
Tier: execution
Obligations: satisfy P3, P7; keep P1
Biggest unknown: <what fails first if an assumption is wrong>
Files: `src/sync.ml`, `test/test_sync.ml`
Interfaces: `val pull : client -> since:int64 -> item list` (src/sync.mli)
Acceptance:
- P3: `dune test -- -only P3` passes
- P7: `dune test -- -only P7` passes
Out of scope: retries (step 3), auth refresh
Hand off: if pagination is not cursor-based, stop and return the failure report
Proof: preserves `kb/models/sync.md#I2` (the cursor never moves backwards)
  Argument: induction on pulls; each pull sets the cursor to max(old, last item)
  Refinement: `Sync.t.cursor` is the model cursor; `Sync.pull` is `pull`
```

| Field | Execution-tier rule |
|---|---|
| Files | every file to create or touch, as backticked paths |
| Interfaces | the signatures, types, CLI flags or wire shapes it exposes or consumes, spelled out |
| Acceptance | one item per criterion, each with the exact command that checks it |
| Out of scope | what it must not touch, so it does not "helpfully" widen the change |
| Hand off | the condition under which it stops instead of deciding |
| Proof | a cited model invariant, the argument and the refinement map; see [proof-ready design](proof-ready-design.md) |

Judgment steps need only Tier, Acceptance and Proof. An execution step must not contain
open-choice wording such as "choose", "decide", "TBD", "as needed" or "etc." in
any field except Out of scope, Hand off and Biggest unknown. Those three fields
exist to name choices.

## Gates

1. `python3 tools/plan-check.py kb/plan.md` exits 0. This checks the shape only.
2. **Execution-tier simulation.** The plan-simulation subagent for execution
   steps runs on the execution model, with the plan and the KB and nothing else.
   It walks each step and lists every question it would have to answer.
   If it lists any question, the step is not ready: settle the question in the
   plan or KB, or change the step to `judgment`. Never answer it only in chat.
3. During Phase 4, an execution agent that hits a Hand off condition, or needs a
   choice the step does not settle, returns the failure report. The planner fixes
   the step, and the executor does not guess.

## What this does not guarantee

A step that passes both gates can still settle a choice wrongly, or name a
command that does not really test its criterion. It also does not show that the
execution model can do this task class. Rule 3's capable reference and the
two-attempt handoff budget still apply.
