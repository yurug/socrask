---
id: properties-edge-cases
type: constraint
summary: <one sentence -- what class of boundary condition this file holds>
domain: <topic>
tags: [<tag>, ...]              # from the controlled vocabulary in GLOSSARY.md
last-updated: YYYY-MM-DD
related: [properties-functional]
---

# Edge cases

Boundary conditions and the behavior expected at each. Every `T<n>` names the
test that pins it — the channel vocabulary and its lint codes are documented
once, in `functional.md`.

Edge cases are the entries where `none:` is least defensible: a boundary you
can describe is a boundary you can write an input for.

T-entries are often a table rather than a section per case. That works — give
the table an `Enforced-by` column and `kb-lint` reads it per row. Claims stated
as bullets are read the same way, from the bullet's own block.

## T1: <the boundary, named>

**Input.** <empty, maximal, unicode, concurrent, malformed -- be concrete>

**Expected behavior.** <exactly what happens, including the exit code or error>

Enforced-by: test:tests/<module>.test.ts::T1

## T2: <the next boundary>

**Input.** <...>

**Expected behavior.** <...>

Enforced-by: test:tests/<module>.test.ts::T2

## Agent notes

> Every T-entry gets a test in Phase 4, not Phase 5 -- these are the cases a
> passing happy path hides.

## Related files

- `functional.md` -- P<n> invariants, and the `Enforced-by:` vocabulary
- `non-functional.md` -- NF<n> measurable criteria
- `INDEX.md` -- routing table for this directory
