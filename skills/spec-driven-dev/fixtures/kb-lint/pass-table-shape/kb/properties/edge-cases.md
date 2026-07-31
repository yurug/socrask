---
id: fixture-props-pass-table-shape
type: constraint
summary: Table-shaped claims, where the channel is a column rather than a line.
domain: fixtures
last-updated: 2026-07-28
---
# Edge cases

Hyphenated IDs (`T-1`) are the same claim shape as `T1`; both are read.

| ID | Boundary | Expected behavior | Enforced-by |
|----|----------|-------------------|-------------|
| T-1 | Empty input | exits 0, prints nothing | test:tests/cli.test.ts::T1 |
| T-2 | Input larger than the buffer | streams, never buffers whole | test:tests/cli.test.ts::T2 |

## Related files

- `INDEX.md` — routing table
