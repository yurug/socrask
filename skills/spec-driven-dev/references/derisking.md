# Derisking: think slow, act fast

## Contents

- [The arc](#the-arc)
- [The preliminary plan](#the-preliminary-plan)
- [The derisking loop](#the-derisking-loop)
- [The risk register](#the-risk-register)
- [Exit](#exit)
- [What is not checked](#what-is-not-checked)

## The arc

Large projects fail during delivery, but the cause is usually in the planning: a
risk that nobody tested before the build started. Flyvbjerg and Gardner (*How Big
Things Get Done*, 2023) found that successful projects plan slowly and deliver
quickly. They test ideas in planning, where an experiment is cheap and a failure
costs a draft. Delivery is short, so the time in which an unexpected event can
derail the project is short too.

The process has five stages, in this order:

| Stage | Speed | Phases | Output |
|---|---|---|---|
| 1. Design | fast | 0, 0.5, 0.75, 1 (first pass) | the goal, the main design choices, the assumptions |
| 2. Preliminary plan | fast | 1.5 | rough steps and the risk register |
| 3. Derisking | fast iterations, back to 1 | 1.5 | each high risk retired by an experiment, or accepted |
| 4. Derisked plan | slow, rigorous | 2, 3 | the KB and an execution-ready plan, with quality and productization planned |
| 5. Execution | efficient | 4 to 7 | the product, built by the cheapest tier that the plan allows |

Stages 1 to 3 are a loop. An experiment can change the design, and a changed
design changes the plan and its risks. Stage 4 starts only when the loop is stable.

The arc runs in every cycle, not once per project. Each feature, slice or milestone
goes through the five stages again, at its own scale: its design is a change to the
existing KB, its experiments retire its own risks, and its plan is derisked before its
execution starts. A cycle that starts at the plan because "the project was already
derisked" has skipped the risks that are new to it.

Stages 1 to 3 are cheap because their outputs are drafts. Stage 4 is expensive
because its outputs bind: the KB, the proof sketches, the execution-ready steps.
Spend that effort only on a design that survived its experiments. Stage 5 is
efficient because stage 4 left no choice open. An execution agent that has
nothing to decide can be a cheaper model, and it converges in fewer iterations.

## The preliminary plan

Write it in minutes, not hours. It is a draft that the derisking loop will change.

- **Start from the goal.** State the outcome that the user or the system must
  observe, then work back to what must exist for it. Do not start from the
  components that are easy to build.
- **Rough steps.** Name the parts and their order, without proof sketches or
  execution detail.
- **Risks.** For each step, ask what could invalidate it: an external API that
  does not behave as documented, an algorithm that does not scale, a data shape
  that cannot represent a case, a user who does not understand the interface, a
  cost or latency budget. Write each one in `kb/risks.md`.
- **Estimate from a reference class.** If `task-meter.py` or `retro.py` has data
  on similar past tasks, start from those actual numbers, then adjust. Do not
  start from what this task looks like from the inside: that view ignores the
  delays that every past task had.

## The derisking loop

For each open risk, in order of probability times impact:

1. **Choose the cheapest experiment that answers it.** A call to the real API, a
   spike that runs the algorithm on adversarial input, a benchmark, a paper
   simulation of the plan by a fresh agent, a prototype or a mock shown to a user,
   a search for prior work. Prefer the experiment that gives an answer in the
   shortest time.
2. **Timebox it.** Write the question and the time limit before you start. When
   the limit is reached without an answer, that is a result too: the risk is
   larger than thought.
3. **Throw the code away.** Spike code answers a question; it is not the first
   version of the product. Keep it on a throwaway branch or in a scratch directory,
   never in the source tree. The register keeps the answer, not the code. Stage 4
   rewrites what it needs, under the code rules.
4. **Record the answer** in the register: the risk is retired, with the evidence
   (a test, a measurement, a report, an `external/` note), or it is larger than
   thought.
5. **Go back to the design** when the answer contradicts it. Change the design,
   update the preliminary plan, and write the new risks. A loop that never
   changes the design is a loop that tested only safe risks.

Do not continue into stage 4 with a high risk open. If no experiment can retire a
risk before delivery, present it to the engineer with its probability, impact and
mitigation. The engineer accepts it or changes the scope. An accepted risk is a
decision with a record, not an assumption.

## The risk register

`kb/risks.md`, from `templates/kb/risks.md`. One table, one row per risk:

| Column | Content |
|---|---|
| ID | `R<n>` |
| Risk | what could invalidate the plan, as a sentence |
| Impact | `high`, `medium` or `low` |
| Experiment | the question and the experiment that answers it |
| Status | `open`, `retired` or `accepted` |
| Evidence | for `retired`: the test, measurement or report; for `accepted`: the engineer's decision (`forebrief:<card-id>` or the date and words) |

The register accumulates across cycles: rows retired in earlier cycles stay, with
their evidence. Write only the risks of the current cycle and of past ones. The risks
of a later milestone go in the roadmap; they enter the register when that milestone's
cycle starts.

`plan-check.py` reads it when it exists. It fails when a high-impact risk is open,
when a retired risk has no evidence, or when an accepted risk has no decision.

## Exit

The loop is stable when:
- no high-impact risk is `open`;
- the last iteration did not change the design;
- `python3 tools/assumption-check.py kb/assumptions.md --exit` passes. An experiment
  can settle an assumption: cite its evidence in the ledger row.

Then stage 4 starts: Phase 2 builds the KB of the design that survived, and Phase 3
writes the derisked plan.

Proportionality: a Slice whose preliminary plan has no high-impact risk skips the
loop, and says so in one line. A Direct change skips stages 1 to 4.

## What is not checked

`plan-check.py` checks the register's shape and statuses, not that the list of risks
is complete, that an experiment really answers its risk, or that the impact is rated
honestly. The independent plan simulation and the plan premortem in Phase 3 look for
missing risks. A surprise during execution is a missing risk: Phase 4 routes it back
to this loop.
