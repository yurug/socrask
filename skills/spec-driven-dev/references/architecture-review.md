# Architecture review

Agents optimize locally. Each slice adds code where it is easiest, inside the
scope it received, and no agent sees the whole system. The structure then erodes
without anyone deciding it. The architecture review asks, at fixed moments,
whether the structure still fits the system and the product.

## What the KB holds

- `kb/architecture/drivers.md`: the product requirements and quality attributes
  that shape the structure, such as latency, availability, evolvability, security
  and expected volume. They come from the non-functional properties and the
  roadmap. Each driver says which structural choice serves it. Start from
  `templates/kb/architecture/drivers.md`.
- `kb/architecture/overview.md`: the component table, with each component's
  paths, declared dependencies, hidden decision and owned state. Start from
  `templates/kb/architecture/overview.md`.
- `kb/architecture/reviews/`: one record per review. Start from
  `templates/kb/architecture/reviews/_TEMPLATE-REVIEW.md`.

## When to review

1. At each roadmap milestone. The milestone names its review in the ledger
   (`architecture_review`).
2. At each Full-tier change, before its Backbrief. No tool can detect the tier,
   so the coordinator runs the review by procedure.
3. When `tools/arch-check.py` reports an erosion signal since the last review:
   hidden coupling between components, or changes scattered over many components.

## How to review

Run it on the judgment tier, and consult the engineer through a forebrief card.

1. Run `python3 tools/arch-check.py --report`. Read the signals and hotspots.
2. Check each driver. Is it still a requirement? Does the structure still serve it?
   A new requirement from the roadmap or the external sources is a new driver.
3. Run `python3 tools/core-check.py --report` when the project declares
   kernels. For each candidate, decide with the engineer: stay at A0, or
   promote by a roadmap task ([formal assurance](formal-assurance.md)).
4. Explain each signal. A coupling is either a missing declared dependency, or a
   decision that two components share and neither hides.
5. Decide with the engineer:
   - **keep**: the record says, per driver, why the structure still fits;
   - **restructure**: write an ADR with the target structure, and add the
     migration to the roadmap as tasks.
6. Write the record with `Covers:` (the HEAD you judged), `Outcome:`, the `ADR:`
   when you restructure, and `Engineer: forebrief:<card-id>`.

## What the check does not do

`arch-check.py` finds symptoms in Git history. It cannot judge whether the
structure is right; only the review does. Signals reset at each review, so a
review that explains nothing still silences them. The engineer's consultation
is the guard against that.
