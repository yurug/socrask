# Engineer-model fallback

Read this reference in full before reading or writing the engineer model when laconic is
unavailable. Keep one concept per file at `~/.laconic/concepts/<id>.md` using this shape:

```markdown
---
id: append-only-recovery
type: concept
domain: storage
state: exposed
confidence: 0.30
evidence:
  - 2026-07-31: asked how replay treats a torn final record
depends-on: [durability]
last-updated: 2026-07-31
---

Replay reconstructs state from durable records in order.

## What the user understands about it

## What has not been established
```

Use lowercase hyphenated IDs, ISO dates, a confidence from 0 to 1, and only the four states
`unknown`, `exposed`, `familiar`, and `verified`. Record an observation, not a conclusion,
under `evidence`; every state above `unknown` requires dated evidence. Never record secrets,
credentials, sensitive conversation content, or an invented observation.

Interpret states conservatively:

- `verified`: use freely without defining;
- `familiar`: use with at most a short first-use gloss;
- `exposed`: define in one clause before relying on it;
- `unknown`: teach before a decision depends on it.

A concept-wide question is evidence that the state is at most `exposed`; a question about one
facet belongs under “What has not been established” and need not erase demonstrated command
of the rest. Correct unprompted use raises confidence by at most one state. Require repeated
independent evidence before `verified`. A direct correction by the engineer overrides the
record immediately.
