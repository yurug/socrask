# Engineer-model fallback

Personal concept records are optional. Obtain owner opt-in before reading or writing
them; otherwise calibrate explanations from the current conversation without storing
a profile. Never export these records to the repository or use them for evaluation.
Questions alone do not justify demotion, and silence is never evidence.

When opted in and laconic is unavailable, keep one concept per file at `~/.laconic/concepts/<id>.md` using this shape:

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

A question may request evidence, challenge an assumption, or clarify scope. It does
not establish misunderstanding. Record a demonstrated misconception only with its
actual context, and revise only the affected facet; correct unprompted use can add
evidence. Require repeated independent evidence before `verified`. A correction
from the owner overrides the record immediately. Omit sensitive content and allow
the owner to inspect or delete the model. Use laconic primarily to make prose
clear, concise, and useful at the current decision point, not to rate the person.
