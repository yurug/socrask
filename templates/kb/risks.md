---
id: risks
type: constraint
summary: The risks that could invalidate the plan, and the experiment that retired each one or the decision that accepted it.
domain: planning
last-updated: YYYY-MM-DD
related: [assumptions, roadmap]
---

# Risk Register

## One-liner
What could invalidate the plan, and how each risk was retired before execution.

## Scope
Covers: risks found in the preliminary plan and in the derisking loop (Phase 1.5).
Does NOT cover: unsettled choices (see `assumptions.md`), schedule (see `roadmap.md`).

## Risks

| ID | Risk | Impact | Experiment | Status | Evidence |
|---|---|---|---|---|---|
| R1 | [What could invalidate the plan] | high | [The question, and the cheapest experiment that answers it] | open | |

## Agent notes
> Retire the high risks before Phase 2: run the experiment, then set `retired` and
> cite the evidence, or change the design and write the new risks. A risk that no
> experiment can retire goes to the engineer, who accepts it (`accepted`, with the
> decision) or changes the scope. `plan-check.py` fails on an open high risk.
> Procedure: `references/derisking.md` in the spec-driven-dev skill.

## Related files
- `assumptions.md` -- choices the KB does not settle; an experiment can settle one
- `roadmap.md` -- the risks of each milestone, and the spikes that open it
