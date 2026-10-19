---
id: observability
type: constraint
summary: What the system logs, in which format, and which events let a failure be traced to its operation and input.
domain: conventions
last-updated: YYYY-MM-DD
related: [architecture-overview, critical-core]
---

# Observability

## One-liner
Every failure can be traced from the events to its operation and input, without reading the code first.

## Event format
- One structured event per line: `at`, `level`, `component`, `operation`, `correlation_id`,
  `input_id`, `result`, and `error` on failure.
- `correlation_id` follows one request or job across components.
- Never log a secret or personal data; log an identifier or a redacted marker.
  `log-check.py` refuses a log call that names a secret-like value.

## Boundary events
| Component | Operation | Event on success | Event on failure |
|---|---|---|---|
| [component] | [operation] | [event name and fields] | [event name and fields] |

## Kernel events
Every rejection by a de Bruijn kernel (see `kb/architecture/critical-core.md`) emits an
event with the output, the rule that failed and the correlation ID. A silent rejection
hides exactly the failures that matter.

## Metrics
| Metric | Why it matters | Alert threshold |
|---|---|---|
| [critical output rate / rejection rate / latency] | [what it detects] | [value] |

## Agent notes
> A production defect starts from the events. If the events cannot locate it, the fix
> adds the missing event, and its regression test asserts that the event is emitted.
