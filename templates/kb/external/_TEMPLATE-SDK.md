---
id: <system>-sdk
type: external
summary: How the <system> SDK actually behaves at runtime -- lazy-loading, pagination, rate limits, request costs.
domain: external
last-updated: YYYY-MM-DD
depends-on: []
related: [architecture-overview]
---

# [System] SDK -- Runtime Behavior

## One-liner
How the [system] SDK actually behaves at runtime, not just its public API.

## Scope
Covers: lazy-loading, pagination, rate limiting, batching, request cost model.
Does NOT cover: business logic built on top of this SDK (see `spec/` files).

## Lazy-loading behavior
[Do relation fields trigger separate API calls? List each one.]
- `.field1` -- [triggers API call? yes/no]
- `.field2()` -- [triggers API call? yes/no]

## Pagination
- Page size: [N]
- Cursor-based / offset-based: [which]
- How to get all results: [pattern]

## Rate limiting
- Limit: [N requests per minute/second]
- What triggers 429: [conditions]
- Backoff expectations: [what the API expects]

## Batching
- Can multiple entities be fetched in one call? [yes/no, how]
- GraphQL includes available? [yes/no]

## Request cost model
| Operation            | API calls for N items | Formula      |
|----------------------|-----------------------|--------------|
| List all items       | [N/pageSize] pages    | ceil(N/50)   |
| List with relations  | [?]                   | ceil(N/50) + ? |
| Fetch single item    | [?]                   |              |

## Request budget (for a realistic workload)
[e.g., For a workspace with 500 issues:]
- Naive approach: [N] API calls -- [acceptable/too many]
- With bulk-fetch-then-join: [N] API calls -- [acceptable]

## Architectural constraints
- [MUST/MUST NOT statements derived from the above]
- e.g., "MUST bulk-fetch users/labels/states once, then join locally"
- e.g., "MUST NOT access .assignee per issue -- use includes or pre-fetch"

## Agent notes
> This file is critical for any code that calls the [system] API.
> The request budget determines whether the architecture needs bulk-fetch-then-join.
> Ignoring lazy-loading behavior leads to N+1 patterns and rate-limit failures.

## Related files
- `architecture/overview.md` -- where this integration fits
- `spec/api-contracts.md` -- our interface contracts built on top of this SDK
