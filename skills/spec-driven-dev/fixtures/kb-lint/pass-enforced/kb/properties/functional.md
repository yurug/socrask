---
id: fixture-props-pass-enforced
type: constraint
summary: Properties whose Enforced-by channels resolve to files that exist.
domain: fixtures
last-updated: 2026-07-28
---
# Functional properties

## P1: A sync never drops a record

A record present before a sync is present after it.

Enforced-by: test:tests/sync.test.ts::P1

## NF1: A full sync costs under 100 API calls

### Statement

The nested heading exercises section ownership: the channel below still
belongs to NF1.

**Enforced-by:** mechanical:tools/check-budget.sh
