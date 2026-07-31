---
id: <stable-unique-id>          # never changes once committed
type: <concept|decision|constraint|procedure|spec|external|index|glossary>
summary: <one sentence -- the claim or fact this file establishes>
domain: <topic>
tags: [<tag>, ...]              # from the controlled vocabulary in GLOSSARY.md
last-updated: YYYY-MM-DD
depends-on: [<id>, ...]         # what this file assumes
refines: [<id>, ...]            # what this file makes more precise
related: [<id>, ...]            # weakly related, no semantic claim
---

# Title (a complete claim, mirrors the filename)

## One-liner
[What this covers in one sentence]

## Scope
What IS covered here. What is NOT (with pointer to where it lives).
What breaks if an assumption in `depends-on` fails.

## Key concepts
- **[Glossary term]** -- see `GLOSSARY.md#term`; [why it matters in this file]
- **[File-local term]**: [definition -- only for terms that appear nowhere else]

## [Content sections]
...

## Agent notes
> When working with this, also check: `<related-file>`
> Gotcha: [something non-obvious that catches implementers]

## Related files
- `<file>` -- why it's relevant
