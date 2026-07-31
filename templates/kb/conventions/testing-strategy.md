---
id: testing-strategy
type: constraint
summary: How, what, and at what level we test -- mocking rules, naming, and coverage targets.
domain: conventions
last-updated: YYYY-MM-DD
related: [properties-index, by-task]
---

# Testing Strategy

## One-liner
How, what, and at what level we test -- including mocking rules and coverage targets.

## Scope
Covers: test levels, naming conventions, mocking policy, coverage targets, property traceability.
Does NOT cover: specific test implementations (those live in `tests/`).

## Test levels

### Unit tests
- One test file per source file
- Mock all external dependencies (use typed mocks matching real interfaces)
- Test individual functions in isolation

### Integration tests
- Test module interactions with real (or near-real) dependencies
- At least one test must hit the real external API (read-only)
- Mocks passing does NOT guarantee the real integration works

### Property-based tests
- For critical invariants, use randomized inputs
- Name with property reference: `"P4: roundtrip preserves all fields"`
- Group in describe blocks: `describe("P2: No data loss")`

### Edge-case tests
- Every T-entry from `properties/edge-cases.md` must have a dedicated test
- Test boundary conditions: empty inputs, unicode, very large inputs, malformed data

### Error-path tests
- Every custom error type must have a test verifying it's thrown with the correct user message
- Test error propagation through the call stack

## Naming convention
Every test name starts with the property or spec reference it verifies:
`"P4: frontmatter->remote->frontmatter roundtrip preserves all fields"`

## Coverage targets
- Line coverage >= 80%
- At least 3 tests per source file on average
- Every property in `properties/` covered by at least 2 tests (one happy path, one edge case)

## Agent notes
> When writing tests, always check `properties/INDEX.md` first to identify which properties
> the module under test must enforce. Missing property coverage is a test gap.

## Related files
- `properties/INDEX.md` -- what must be tested
- `properties/edge-cases.md` -- boundary conditions to cover
- `spec/error-taxonomy.md` -- error types to test
