---
id: properties-non-functional
type: constraint
summary: <one sentence -- what class of measurable criterion this file holds>
domain: <topic>
tags: [<tag>, ...]              # from the controlled vocabulary in GLOSSARY.md
last-updated: YYYY-MM-DD
related: [properties-functional]
---

# Non-functional properties

Measurable criteria: latency, cost, limits, availability. Every `NF<n>` states
a number and names what measures it — the channel vocabulary and its lint codes
are documented once, in `functional.md`.

An NF whose only channel is `none:` is an aspiration. If a criterion is
measurable enough to write down, the measurement is usually a script: a timer
in a test, a counter in CI, a request-budget check against `../external/`.

## NF1: <the criterion, with its number>

**Statement.** <the measurable claim -- a threshold, not an adjective>

**How it is measured.** <the workload, the units, where the number comes from>

**Why this number.** <what breaks above it>

Enforced-by: mechanical:tools/<checker>.sh

## NF2: <the next criterion>

**Statement.** <...>

**How it is measured.** <...>

**Why this number.** <...>

Enforced-by: test:tests/<module>.perf.test.ts::NF2

## Agent notes

> A request-budget NF is checked against the numbers in `../external/` -- if
> the SDK research says a full sync costs 340 calls and NF1 caps it at 100, one
> of the two files is wrong and the contradiction is the finding.

## Related files

- `functional.md` -- P<n> invariants, and the `Enforced-by:` vocabulary
- `edge-cases.md` -- T<n> boundary conditions
- `INDEX.md` -- routing table for this directory
