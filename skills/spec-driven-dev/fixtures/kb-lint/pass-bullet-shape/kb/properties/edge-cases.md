---
id: fixture-props-pass-bullet-shape
type: constraint
summary: Bullet-shaped claims — the shape a heading-only checker walks straight past.
domain: fixtures
last-updated: 2026-07-28
---
# Edge cases

- **T1** `../` traversal (`../../etc/passwd`) → denied, exit 5.
  Enforced-by: none: the traversal cases are exercised by hand each release
  because the fuzzer cannot reach this path
- **T2** absolute path outside root → denied. Enforced-by: none: same manual
  pass as T1, and for the same reason

## Related files

- `INDEX.md` — routing table
