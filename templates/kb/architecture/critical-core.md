---
id: critical-core
type: constraint
summary: The outputs whose error costs a lot, and the small kernel that checks each one before it takes effect.
domain: architecture
last-updated: YYYY-MM-DD
related: [architecture-overview]
---

# Critical core

## One-liner
Each critical output passes through a small, specified, replicable checker before it takes effect.

## Criticality analysis
List the outputs whose error costs a lot: money, data, safety, an irreversible action.
For each one, say what the error costs and why a checker can decide it.

## Kernels

Checked by `core-check.py` (spec-driven-dev). Paths are written from the repo root.
Assurance is A0 (tests), A1 (model proved) or A2 (checker extracted from the proof);
A1 and A2 name the proof files and the commit at which the proof built.

| Output | Checker | Budget | Spec | Assurance | Proof | Proved at |
|---|---|---|---|---|---|---|
| [critical output] | `[path/to/checker]` | [max lines] | `kb/models/[model].md` | A0 | - | - |

## Agent notes
> A kernel change runs on the judgment tier with human review; `plan-check.py` refuses
> an execution step that touches a kernel file. The kernel must not depend on its
> producer. See `references/component-design.md` in the spec-driven-dev skill.
> A change to an A1 or A2 kernel, its model or its proof voids the claim until the
> proof is checked again (`references/formal-assurance.md`).
