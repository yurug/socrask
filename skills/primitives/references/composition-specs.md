# Rail, lanes, and layers specs

These three DOM renderers cover order, ownership, and boundaries without
turning each problem into a graph. Import the renderer from its own entry so a
DOM-only visual does not pull Graphviz or Vega into the bundle.

## Contents

- [Shared envelope](#shared-envelope)
- [Rail](#rail)
- [Lanes](#lanes)
- [Layers](#layers)
- [Render and handle outcomes](#render-and-handle-outcomes)

## Shared envelope

Every spec starts with:

```json
{
  "schemaVersion": "0.4.0",
  "kind": "rail",
  "trust": "grounded",
  "title": "An answer becomes context"
}
```

Use the `PRIMITIVES_SCHEMA_VERSION` exported by `@brief/primitives` when the
spec is created in code. `title` is optional. `trust` is `grounded` or
`conjecture`; the renderer makes that status visible at the evidence boundary.

## Rail

Use a rail for one dominant order. It accepts 2–7 stops. Keys must be unique;
`focus`, when present, must name one of them.

```json
{
  "schemaVersion": "0.4.0",
  "kind": "rail",
  "trust": "grounded",
  "title": "An answer becomes context",
  "stops": [
    { "key": "ask", "label": "Agent asks", "meta": "00:00" },
    { "key": "answer", "label": "Human answers", "meta": "00:12" },
    {
      "key": "wake",
      "label": "Sentinel wakes",
      "detail": "The event is noticed without another prompt."
    },
    { "key": "resume", "label": "Agent resumes", "meta": "00:13" }
  ],
  "focus": "wake"
}
```

Each stop requires `key` and `label`; `meta` and `detail` are optional. Do not
use a rail when the path branches—the loss of branching is deliberate.

## Lanes

Use lanes when actors persist while phases advance. It accepts 2–7 phases,
2–5 lanes, and at most one activity in each lane/phase cell. A hand-off must
reference two existing activities in different lanes.

```json
{
  "schemaVersion": "0.4.0",
  "kind": "lanes",
  "trust": "grounded",
  "title": "Who owns attention?",
  "phases": [
    { "key": "ask", "label": "Ask" },
    { "key": "act", "label": "Act" },
    { "key": "notice", "label": "Notice" },
    { "key": "resume", "label": "Resume" }
  ],
  "lanes": [
    { "key": "agent", "label": "Agent" },
    { "key": "human", "label": "Human" },
    { "key": "sentinel", "label": "Sentinel" }
  ],
  "activities": [
    {
      "key": "prompt",
      "lane": "agent",
      "phase": "ask",
      "label": "Requests a choice"
    },
    {
      "key": "answer",
      "lane": "human",
      "phase": "act",
      "label": "Submits an answer",
      "tone": "signal"
    },
    {
      "key": "detect",
      "lane": "sentinel",
      "phase": "notice",
      "label": "Detects the event",
      "tone": "accent"
    },
    {
      "key": "continue",
      "lane": "agent",
      "phase": "resume",
      "label": "Uses the response",
      "tone": "success"
    }
  ],
  "handoffs": [
    { "from": "prompt", "to": "answer", "label": "browser" },
    { "from": "answer", "to": "detect", "label": "event" },
    { "from": "detect", "to": "continue", "label": "wake" }
  ]
}
```

An activity may also have `detail`. Its optional `tone` is `neutral`,
`accent`, `signal`, or `success`; use tones semantically, not for variety.

## Layers

Use layers for ordered responsibility or abstraction boundaries. It accepts
2–5 layers, each with 1–6 items. Layer and item keys must be unique. The
optional sidecar is one concern that crosses the whole stack.

```json
{
  "schemaVersion": "0.4.0",
  "kind": "layers",
  "trust": "grounded",
  "title": "Attention is infrastructure",
  "layers": [
    {
      "key": "interaction",
      "label": "Interaction",
      "items": [{ "key": "browser", "label": "Browser action" }]
    },
    {
      "key": "durability",
      "label": "Durability",
      "caption": "Events survive the request cycle.",
      "items": [{ "key": "events", "label": "Brief event server" }]
    },
    {
      "key": "attention",
      "label": "Attention",
      "items": [
        { "key": "sentinel", "label": "Human-event sentinel", "tone": "accent" }
      ]
    }
  ],
  "sidecar": {
    "label": "Evidence boundary",
    "statement": "No visible response should depend on being announced twice.",
    "tone": "accent"
  }
}
```

An item tone and the sidecar tone may be `accent`, `signal`, or `success`.
Do not duplicate a crossing concern into every layer; that is the sidecar's
job.

## Render and handle outcomes

```ts
import { renderRail } from "@brief/primitives/rail";

const outcome = renderRail(spec);
if (outcome.status === "invalid") throw outcome.error;
artifact.innerHTML = outcome.html; // `ok` or the actionable skew banner
```

Use `renderLanes` from `@brief/primitives/lanes` and `renderLayers` from
`@brief/primitives/layers` in the same way. The renderers escape text, stamp
provenance, render trust, reject unknown fields, and return byte-deterministic
HTML.
