---
id: <subsystem>-model
type: spec
summary: Proof-ready abstract model of <subsystem> -- state, operations, invariants, refinement map.
domain: <domain>
last-updated: YYYY-MM-DD
depends-on: []
related: [architecture-overview]
---

# [Subsystem] -- Model

## One-liner
The abstract model a proof of [subsystem] starts from, and how the code maps onto it.

## Scope
Covers: [the state and operations of this subsystem].
Does NOT cover: [neighbouring subsystems; I/O at the edges].

## State
- `[name]`: [set / map / sequence / record over abstract types].

## Operations
- `[op](args)`: requires [precondition]; sets [state change].

## Invariants
- **I1**: [statement over the state]. Every operation above preserves it.

## Refinement map
- `[code value]` represents `[model value]`.
- `[code entry point]` implements `[op]`.

## Proof notes
Trusted: [what the argument assumes, e.g. the clock is monotonic].
Not covered: [what the argument leaves out].

## Agent notes
> Plan steps cite invariants as `kb/models/<this file>.md#I<n>`. Keep this model
> small enough to transcribe into Rocq or Lean in one sitting. See
> `references/proof-ready-design.md` in the spec-driven-dev skill.
