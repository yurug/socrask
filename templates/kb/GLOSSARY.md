---
id: glossary
type: glossary
summary: Canonical definitions for every domain term, plus the controlled tag vocabulary used in KB frontmatter.
domain: meta
last-updated: YYYY-MM-DD
related: [index]
---

# Glossary

## One-liner
Canonical definitions for every domain term used across the KB, and the controlled tag vocabulary.

## Scope
All terms that appear in more than one KB file. Terms specific to a single file are defined inline in that file.

## Terms

- **[Term]**: [Definition]. See also `[related-file]`.

## Controlled tag vocabulary

Every value in a KB file's `tags:` frontmatter MUST come from this list. Add a tag here
before using it; keep the list small (a tag used by only one file is not a tag, it's noise).

- `[tag]` -- [what files carry it]

## Agent notes
> Load this file early -- it prevents misinterpretation of domain terms across the KB.
> If a term is ambiguous or used inconsistently, fix it here first and update all references.

## Related files
- `INDEX.md` -- master routing
