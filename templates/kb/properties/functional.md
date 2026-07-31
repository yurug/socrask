---
id: properties-functional
type: constraint
summary: <one sentence -- what class of invariant this file holds>
domain: <topic>
tags: [<tag>, ...]              # from the controlled vocabulary in GLOSSARY.md
last-updated: YYYY-MM-DD
---

# Functional properties

Invariants the system must hold. One `P<n>` per property, each naming the
machinery that holds it.

## How to declare enforcement

Every `P<n>` carries at least one `Enforced-by:` line. `kb-lint` fails the
build on a property that carries none (`E-unenforced`), names a channel outside
the closed set (`E-channel`), names a file that does not exist (`E-channel`),
or says `none:` without a real reason (`E-noreason`).

```
Enforced-by: structural:<path>             a type/constructor/capability that makes
                                           the violation unrepresentable
Enforced-by: proof:<path>                  a machine-checked obligation; also write
                                           what it does NOT cover (see below)
Enforced-by: test:<path>::<test name>      a test that fails when the property breaks
Enforced-by: mechanical:<path>[#<code>]    a linter, checker, or CI script
Enforced-by: hook:<path>                   a hook that fires during a session
Enforced-by: none: <why not, in a sentence>
```

The list is ordered strongest-first and the order is a recommendation. A wrong
answer that cannot be represented beats one that is merely caught: a structural
channel needs no maintenance, cannot be skipped, and does not rot. Before writing
a test, spend a minute on whether a type could make the violation impossible.

A `proof:` channel is universal over the property *as stated*, under the
assumptions its kernel and extraction carry — so name what it leaves out on a
`Trusted:` or `Not covered:` line. `kb-lint` warns (`W-trust`) when a proof
channel has no such line, because an unnamed boundary reads as a guarantee over
the whole system, which is the one thing it is not.

The vocabulary is closed and `instruction:` is deliberately absent. Prose in a
project's CLAUDE.md raises a probability; it does not hold an invariant, and admitting
it as a channel would let every property pass by pointing at a paragraph. When
prose really is all there is, `none: <reason>` is the honest declaration — and
the reason is what the next audit reads before deciding whether the gap is
still acceptable.

Reach for `none:` last. A property with no checker is usually a property nobody
has written the thirty-line script for yet: a `grep` in CI, a hook that reads
the diff, a counter with a threshold. Writing that script is ordinary work, not
a project, and the kit's own `tools/primitives-adoption.sh` is what one looks
like — a crude, inspectable count with a number that stops the build.

A property may declare several channels. More than one is a claim that the
property is held from more than one side, so say it when it is true.

## P1: <a complete claim, in the present tense>

**Statement.** <what must always be true>

**Violation example.** <a concrete input or sequence where it would break>

**Why.** <what goes wrong downstream if this does not hold>

Enforced-by: test:tests/<module>.test.ts::P1

## P2: <the next invariant>

**Statement.** <...>

**Violation example.** <...>

**Why.** <...>

Enforced-by: mechanical:tools/<checker>.py#<code>
Enforced-by: none: <the part the checker cannot see, and why that is acceptable>

## Agent notes

> Test names start with the property ID (`"P4: roundtrip preserves fields"`),
> so a failing test names the invariant it broke without anyone consulting this
> file. Code that enforces a property carries `@invariant P<n>`.
> A property whose channel is `none:` is the first thing a Phase 5 audit should
> look at — it is the part of the spec with nothing standing behind it.

## Related files

- `non-functional.md` -- NF<n> measurable criteria (latency, cost, limits)
- `edge-cases.md` -- T<n> boundary conditions and their expected behavior
- `INDEX.md` -- routing table for this directory
