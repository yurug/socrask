---
id: code-style
type: constraint
summary: How source files are cut, explained and tested so that an engineer understands each one alone.
domain: conventions
last-updated: YYYY-MM-DD
related: [testing-strategy, audit-checklist, method]
---

# Code Style

## One-liner
Each source file is one cohesive concept that an engineer understands without the KB.

## Scope
Covers: module boundaries, comments and documentation, unit tests per module, gardening
before a change, and the language rules of this project.
Does NOT cover: test levels and naming (see `testing-strategy.md`), log format (see
`observability.md`).

## The reader
An engineer who opens one source file. They have not read the KB, the spec, the plan or
the agent's session. Every rule below serves this reader.

## Rules

### Cohesion decides the boundaries, not size
- A module holds one concept and everything that changes with it.
- Split a module whose purpose needs two independent clauses joined by "and".
- Merge two files that a reader must open together, or that always change in the same
  commit. A file that only forwards, or holds one helper for one user, hides nothing:
  put its content beside its user.
- Size is a review trigger, not a limit: a file over ~400 lines states why it is one
  concept; a new file under ~50 lines with one caller states what it hides.

### Local comprehension
- A KB reference follows a claim written in words; it never replaces it.
  Good: `// The cursor never decreases, so a retry never emits an event twice (P4).`
  Bad: `// enforces P4`.
- Plain words, or a project term defined on first use in the file. No step, slice or
  finding labels.
- Comments describe the code as it is. History goes in commit messages.
- At a call that relies on a property of the callee, state that property there.

### Literate at the right level
- File header: the problem, the approach and why it beats the obvious alternative, the
  invariants, what the module does not do. A worked example if the module is tricky.
- Public functions: the contract (parameters, result, errors, preconditions), in the
  format of [the ecosystem's doc tool].
- Inside an algorithm: comments name its phases and say why each is needed. No comment
  restates the next line.
- Central type and entry point first, helpers after, where the language allows it.

### Unit tests per module
Each module has unit tests on its interface, one per case of its contract. See
`testing-strategy.md`.

### Garden before you change
Before changing a file that breaks these rules where you change it: add characterization
tests if its contract has none, refactor without changing behavior, and commit that alone
(`garden: <file>: <what improved>`). Then make the change. Budget: about as much as the
change itself. A larger rework becomes a roadmap item.

## Language rules
[Fill for this project: doc comment format, interface files or export rules that enforce
information hiding, forbidden constructs (e.g. `any`), formatter and linter.]

## Agent notes
> Read this file before writing or changing code. In review, the cold-read audit checks
> the first three rules: a fresh reader gets the changed file alone and must explain what
> it does, how, and why.

## Related files
- `conventions/testing-strategy.md` -- unit test expectations
- `runbooks/audit-checklist.md` -- the code-quality checks
- `conventions/method.md` -- project rules that refine these
