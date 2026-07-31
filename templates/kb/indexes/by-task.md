---
id: by-task
type: index
summary: Given a task type (implement, audit, test, debug), the exact KB files to load and in what order.
domain: meta
last-updated: YYYY-MM-DD
related: [index]
---

# Task-Oriented Index

## One-liner
Given a task type, tells you exactly which KB files to load and in what order.

---

## `implement`

### Add a new module / feature
1. `architecture/overview.md` -- understand module structure and patterns
2. `spec/INDEX.md` -- pick the relevant spec file for this feature
3. `external/INDEX.md` -- if touching a third-party integration, load the SDK file
4. `properties/INDEX.md` -- identify invariants this module must enforce
5. `conventions/code-style.md` -- naming, structure, patterns
6. `conventions/error-handling.md` -- error types, propagation

**Key questions this answers:** What does this module do? What invariants must it maintain? What are the SDK constraints?

---

## `audit`

### Security audit
1. `runbooks/audit-checklist.md`
2. `conventions/error-handling.md` -- how errors are exposed
3. `architecture/overview.md` -- entry points, trust boundaries
4. `external/INDEX.md` -- credential handling per SDK

### Spec compliance audit
1. `domain/prd.md` -- what should exist
2. `spec/INDEX.md` -- how it should work
3. `properties/INDEX.md` -- what must always be true

**Key questions this answers:** Where are the attack surfaces? Does the code match the spec?

---

## `test`

### Write or fix tests
1. `conventions/testing-strategy.md` -- test levels, mocking rules
2. `properties/functional.md` -- invariants to test
3. `properties/edge-cases.md` -- boundary conditions to cover
4. `spec/error-taxonomy.md` -- error paths to test

**Key questions this answers:** What must be tested? At what level? What edge cases exist?

---

## `debug`

### Debug an integration issue
1. `external/INDEX.md` -- pick the relevant SDK file
2. `spec/api-contracts.md` -- expected inputs/outputs
3. `architecture/overview.md` -- where this integration fits

### Debug a logic issue
1. `spec/algorithms.md` -- expected behavior
2. `properties/functional.md` -- which invariant is violated
3. Relevant `domain/` file

**Key questions this answers:** What should happen? What does the SDK actually do? Which invariant broke?

## Agent notes
> This is the core navigation file. Keep it updated as task types evolve.
> When adding a new domain or external integration, add corresponding entries here.

## Related files
- `INDEX.md` -- master routing (has quick-load bundles for common goals)
