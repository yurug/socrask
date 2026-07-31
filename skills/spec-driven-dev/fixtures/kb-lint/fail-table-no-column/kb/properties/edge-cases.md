---
id: fixture-props-fail-table-no-column
type: constraint
summary: A claim table with no channel column — the silent shape, now loud.
domain: fixtures
last-updated: 2026-07-28
---
# Edge cases

| ID | Boundary | Expected behavior |
|----|----------|-------------------|
| T1 | Empty input | exits 0, prints nothing |
| T2 | Input larger than the buffer | streams, never buffers whole |

## Related files

- `INDEX.md` — routing table
