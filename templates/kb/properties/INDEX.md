---
id: properties-index
type: index
summary: Routing table for the properties directory — invariants, measurable criteria, boundaries.
domain: <topic>
tags: [<tag>, ...]              # from the controlled vocabulary in GLOSSARY.md
last-updated: YYYY-MM-DD
---

# Properties

What the system must hold, and what holds it.

| If you need... | Read |
|---|---|
| The invariants, and how enforcement is declared | `functional.md` |
| Latency, cost, and limit criteria with their numbers | `non-functional.md` |
| Boundary conditions and expected behavior at each | `edge-cases.md` |

Every entry in these files carries an `Enforced-by:` line naming the test,
script, or hook that holds it — or `none:` with a reason. `kb-lint` fails the
build on an entry that carries none; the vocabulary is defined in
`functional.md`.

## Agent notes

> Implementing a plan step: load the P/NF/T entries the step names, then the
> files their channels point at. The channel tells you where the enforcement
> already lives, so you extend it rather than writing a second checker beside it.

## Related files

- `../conventions/testing-strategy.md` -- how these entries become tests
- `../runbooks/audit-checklist.md` -- the audit that reads the `none:` reasons
