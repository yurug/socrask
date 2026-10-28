# Component design

## Contents

- [The principles](#the-principles)
- [Where the decisions live](#where-the-decisions-live)
- [Review questions](#review-questions)
- [What is not checked](#what-is-not-checked)

These rules shape every component the agent designs or changes. They work with
[proof-ready design](proof-ready-design.md): a small, stateless, well-hidden
component is also the easiest one to state a model for.

## The principles

1. **General and composable.** Prefer a general component with a composable
   interface when it costs no more than the special case. Extract the general
   version at the second real use, not before.
2. **Don't repeat yourself.** Each piece of knowledge has one authoritative place
   in the code. Knowledge means a rule, a format, a constant or an algorithm. Factor a duplicate,
   or keep it with a stated reason. Two pieces of code that are alike by chance
   and change for different reasons are not a duplicate.
3. **Information hiding.** Each component hides one design decision that is
   likely to change, behind its interface. Other components use only that
   interface, never its internal modules or its data representation.
   A change that exposes an internal needs an ADR.
   **Cohesion decides the boundaries, not size.** A module holds one concept and
   everything that changes with it. Each file boundary costs the reader a jump, so
   it must buy a hidden decision. Apply two tests, in both directions:
   - *Split*: if the module's purpose needs two independent clauses joined by "and",
     it holds two concepts. Split it, or state the invariant that binds them.
   - *Merge*: if a reader must open B to understand A, or A and B always change in
     the same commit, they are one concept cut in two. Merge them. A file that only
     forwards or re-exports, or that holds one type, constant or helper with a single
     user, hides nothing: put its content beside its user.
   "Keep components small" is not a rule here. A 600-line parser that is one concept
   is better than six 100-line files that a reader must open together.
4. **De Bruijn kernel.** Find the outputs whose error costs a lot: money, data,
   safety, an irreversible action. Put a small checker between the producer of
   each such output and its effect. The producer can be large and heuristic.
   The kernel accepts or rejects the output, with a witness when one helps.
   The kernel is small, deterministic and independent of the producer. It has a
   clear specification in `kb/models/`, from which someone can rewrite it.
   It gets the strongest assurance: a proof, or property and mutation tests.
   A stable kernel is a candidate for a proof ([formal assurance](formal-assurance.md)).
   Each rejection emits an event: a silent kernel hides the failures that matter.
   Every change to it runs on the judgment tier, with human review.
5. **Minimal, segmented state.** Stateless by default. Each piece of mutable
   state has one owner component, and no other component changes it. In-place
   mutation, overwrite and deletion need a stated reason, such as a measured
   need or an external constraint. Write the reason at the site, or in an ADR
   for a structural choice. Prefer immutable values and append-only records.
   Keep dependencies few: question each new one.
6. **Illegal states unrepresentable.** Types carry the specification. Use
   algebraic data types and abstract types so that invalid values cannot be
   built. Parse each input once at the boundary into a precise type. Inside the
   boundary, trust the type; do not validate again.
7. **Least authority.** A component receives only the capabilities it needs:
   files, network, credentials, permissions. Pass them in explicitly. A kernel
   receives no authority beyond its inputs and its verdict.
8. **Determinism and idempotence.** The same inputs give the same outputs.
   Inject every source of non-determinism explicitly: clock, randomness,
   ordering, environment. An operation that can be retried has the same effect
   once or several times.
9. **Data outlives code.** Every persisted format and protocol carries a
   version. Each version change comes with a migration. Readers tolerate fields
   they do not know. Decide a data shape as an ADR before code writes it.
10. **Observable by design.** Log structured events at component boundaries:
    the operation, a correlation ID, an input identifier, the result. A failure
    in production can then be traced to its operation and input without reading
    the code first. `kb/conventions/observability.md` fixes the format, the
    boundary events and the metrics of critical outputs (start from
    `templates/kb/conventions/observability.md`). Never log secrets or personal
    data; `log-check.py` refuses a log call that names a secret-like value.

## Where the decisions live

`kb/architecture/overview.md` lists, in its component table (format in
[architecture review](architecture-review.md)), for each component:
- its public interface and the design decision it hides;
- the mutable state it owns, if any;
- the authority it receives.

`kb/architecture/critical-core.md` declares each de Bruijn kernel. Start from
`templates/kb/architecture/critical-core.md`. `core-check.py` checks it:

```sh
python3 tools/core-check.py kb/architecture/critical-core.md
```

It refuses a kernel whose checker files or specification do not exist, or whose
checker files exceed the declared line budget. It also refuses a formal
assurance claim that no longer holds; `--report` lists the stable kernels. `plan-check.py` refuses an
execution-tier step whose Files include a kernel file.

## Review questions

The Phase 5 review asks, for each changed component:
- Is there a general component this should use or become?
- Does any knowledge now live in two places?
- Does any other component reach past this interface?
- Does this file boundary hide a decision, or must a reader open both sides
  together? Do these files always change together?
- Does this change touch a critical output without passing through its kernel?
- Does this change add a special case to a general rule so that an acceptance case
  passes? Fix the general rule, or ask the engineer to change the case.
- Does this state need to exist, and who owns it?
- Is each destructive operation justified?
- Can an invalid value of this type be built?
- Does this component hold an authority it does not use?
- Does the result depend on anything not passed in?
- Does this change a persisted format without a version and a migration?
- Can a failure here be traced from the logs?

## What is not checked

Most of these rules depend on the language, so the review checks them, not a
script. The compiler can enforce some of them: interface files (`.mli`), module
privacy, package `exports`, and exhaustive pattern matching. Use those where the
language has them. `core-check.py` cannot check that a kernel does not depend on
its producer, or that the list of critical outputs is complete.
