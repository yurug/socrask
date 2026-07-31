---
id: audit-checklist
type: procedure
summary: Structured checklist for multi-axis quality audits during and after implementation.
domain: runbooks
last-updated: YYYY-MM-DD
related: [by-task, testing-strategy]
---

# Quality Audit Checklist

## One-liner
Structured checklist for multi-axis quality audits during and after implementation.

## Scope
Covers: code quality, test coverage, security, performance, UX, spec compliance.
Does NOT cover: how to fix findings (see conventions/ files for guidance).

## 1. Code Quality

- [ ] Every source file has a module header comment
- [ ] Every public function has complete documentation (params, returns, throws, invariant)
- [ ] Files under ~30% comment ratio checked for missing WHYs (ratio is a smoke alarm, never a target -- no comment that restates the code)
- [ ] No function > 30 lines
- [ ] No file > 200 lines
- [ ] No `any` types (use `unknown` and narrow)
- [ ] Dependency injection everywhere (interfaces, not implementations)
- [ ] No circular imports

## 2. Test Coverage

- [ ] Every source file has a corresponding test file
- [ ] At least 3 tests per source file
- [ ] Every property in `properties/` has at least 2 tests
- [ ] Every edge case in `properties/edge-cases.md` has a dedicated test
- [ ] Every error type has an error-path test
- [ ] At least one integration test hits the real external API
- [ ] Property-based tests exist for critical invariants
- [ ] Test names include property references

## 3. Security

- [ ] Credentials from environment, never hardcoded
- [ ] Credentials never appear in error messages or logs
- [ ] Input validation at system boundaries
- [ ] No data exposure in user-facing error messages

## 4. Performance

- [ ] API calls within request budget (see `external/` files)
- [ ] No N+1 patterns (lazy-loading resolved via bulk-fetch)
- [ ] Pagination handles all results, not just first page
- [ ] Async patterns correct (no unnecessary serialization)

## 5. UX

- [ ] Help text accurate and complete for every command
- [ ] Error messages include the actual cause, not generic wrappers
- [ ] Progress indicators for long operations
- [ ] Exit codes meaningful (0 = success, 1 = partial, 2 = fatal)
- [ ] Dry-run mode clearly labeled

## 6. KB Health

- [ ] `python3 tools/kb-lint.py kb` exits 0 (no errors)
- [ ] Every W-stale warning triaged: file content re-verified against code, `last-updated` bumped
- [ ] KB files touched by this phase's changes were updated in the same commits
- [ ] No rationale blended into `procedure` files; no glossary terms re-defined outside `GLOSSARY.md`

## 7. Spec Compliance

- [ ] Every feature in `spec/` is implemented
- [ ] Every data model field matches `spec/data-model.md`
- [ ] Every error type matches `spec/error-taxonomy.md`
- [ ] Config format matches `spec/config-and-formats.md`

## Agent notes
> Run this checklist after each implementation phase and after quality audits.
> Missing items are findings -- classify as CRITICAL / HIGH / MEDIUM / LOW.
> CRITICAL findings must be fixed before proceeding.

## Related files
- `conventions/code-style.md` -- what "quality" means for code
- `conventions/testing-strategy.md` -- what "coverage" means
- `conventions/error-handling.md` -- how errors should work
