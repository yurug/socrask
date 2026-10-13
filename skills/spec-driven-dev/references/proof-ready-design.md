# Proof-ready design

Most projects never run a proof assistant. The design must still be provably
correct. At any point, someone can start a proof of the underlying model in Rocq
or Lean, and the code maps onto that model. An agent that changes behavior knows
the argument that makes the change correct, and writes that argument down.

## The model

Each subsystem with state or a correctness claim has one file in `kb/models/`.
Start from `templates/kb/models/_TEMPLATE-MODEL.md`. The file has five parts:

| Part | Content |
|---|---|
| State | the abstract state, as sets, maps, sequences and records; no implementation types |
| Operations | each operation with its precondition and its effect on the state |
| Invariants | `I1`, `I2`, ...: statements over the state that every operation preserves |
| Refinement map | which code value represents which model value, and the code entry point for each operation |
| Proof notes | `Trusted:` what the argument assumes; `Not covered:` what it leaves out |

The model is the statement a mechanized proof starts from. Keep it small enough
to transcribe into a proof assistant in one sitting. A property in
`kb/properties/` can cite an invariant (`kb/models/sync.md#I2`) instead of
restating it.

## Design rules

These rules keep the gap between code and model small:

1. Keep a pure core. Effects (I/O, clocks, randomness, network) stay at the edges
   and pass their results into the core as values.
2. Make state explicit. A function receives the state it reads and returns the
   state it changes. No hidden global or mutable state in the core.
3. Write total functions. Every input has a defined result; errors are values.
4. One code entry point per model operation, named in the refinement map.
5. A design choice that breaks the refinement map needs an ADR. The ADR says
   which invariant loses its argument and what replaces it.

## The proof sketch on each step

Every step in `kb/plan.md` has a `Proof:` field:

```markdown
Proof: preserves `kb/models/sync.md#I2` (the cursor never moves backwards).
  Argument: induction on the sequence of pulls; each pull sets the cursor to
  max(old cursor, last item of the page).
  Refinement: `Sync.t.cursor` represents the model cursor; `Sync.pull` is `pull`.
```

- An execution step names at least one invariant by `kb/models/<file>.md#I<n>`,
  an `Argument:` and a `Refinement:`. `plan-check.py` checks that the file and the
  invariant ID exist.
- A judgment step can state what it will establish, for example a new invariant.
- A step with no behavior change writes `Proof: none: <reason>`.
- If the planner cannot write the argument, the step is not ready. Change the
  design or the model first, on the judgment tier.

## During implementation

- Each cited invariant gets a property-based test whose name starts with the
  invariant ID, for example `"I2: cursor never decreases"`.
- If the code needs an argument the sketch does not give, stop. Fix the sketch
  and the model in the plan, in the same commit as the code.
- Review compares the code with the sketch: does the refinement map still hold,
  and does each operation preserve the cited invariants?

## What this does not guarantee

A sketch is not a proof. `plan-check.py` checks that the sketch exists and cites
a real invariant. It does not check the argument. Tests sample the invariant;
they do not prove it. For a critical core, run the proof in an assistant, and
state its boundary as the `Trusted:` and `Not covered:` lines.
