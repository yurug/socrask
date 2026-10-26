# Formal assurance

A de Bruijn kernel makes a proof affordable. The producer can stay large and
heuristic; only the small checker must be right. When a kernel is critical and
has stopped moving, prove it. The proof work runs beside the slices and never
blocks them.

## Assurance levels

`kb/architecture/critical-core.md` gives each kernel a level in its `Assurance`
column. A kernel without the column is A0.

| Level | What is established | What links the code to it |
|---|---|---|
| A0 | property and mutation tests on the checker | the tests |
| A1 | the model in `kb/models/` is transcribed into Rocq or Lean, and its invariants are proved | differential tests: the checker against an executable reference extracted from the proof |
| A2 | the checker is extracted from the proof and replaces the hand-written one | the construction; the extraction and the runtime become trusted |

A checker suits A2 well. Its theorem is short: `check o = true -> spec o`,
soundness of a decision procedure, as in translation validation. A1 proves the
model, not the code: write that gap in the model's `Not covered:` line.

A1 or A2 adds two columns. `Proof` lists the proof files. `Proved at` is the
commit at which the proof built. [rocqeteer](https://github.com/yurug/rocqeteer)
is the reference tool for Rocq proofs.

## When to promote a kernel

Decide during an [architecture review](architecture-review.md), with the
engineer. A kernel is a candidate when all of these hold:

1. Its error costs a lot, and a test sample does not bound that cost well enough.
2. Its specification is decidable and fits the model template.
3. It is stable: `core-check.py --report` shows no commit on its checker, model
   or proof over the window (50 commits by default). A proof of moving code is
   paid again at each change.
4. For A2, the project accepts the extraction language (OCaml, Haskell) at that
   boundary. If not, write an ADR (foreign call or rewrite), or stay at A1.

Record the decision in the review under `## Formal assurance`. A promotion
becomes a roadmap task on the judgment tier. Start with A1. Make A2 the target
only when A1 holds and the differential tests have found no divergence.

## Who reviews what

The proof assistant checks the proof: this is the de Bruijn criterion applied
to the proof itself. An agent can write the proof. The engineer reviews the
statement: the model, its invariants, the theorem and the `Trusted:` line. A
proof of the wrong statement is worth nothing, and only a human can judge the
statement against the product.

## Keeping the claim true

`core-check.py` holds each A1 or A2 claim to the repository:

- the proof files exist, and `Proved at` is a commit;
- no checker, model or proof file changed since `Proved at` (`E-stale`); a
  change means: prove again and move `Proved at`, or declare A0;
- no `.v` or `.lean` proof admits a goal (`Admitted`, `admit`, `sorry`), and
  the model's `Trusted:` line names each axiom it declares (`E-admit`).

CI builds the proof. In Rocq, CI also runs `Print Assumptions` on the main
theorem and compares the result with the `Trusted:` line. The admit scan is
textual; the build is the real check.

## What this does not guarantee

A proof covers the model's statement, under its `Trusted:` assumptions. It does
not cover the effects at the edges, a wrong statement, or, at A1, a divergence
that the differential tests miss. The stability window is a heuristic. The
review decides; the report only proposes.
