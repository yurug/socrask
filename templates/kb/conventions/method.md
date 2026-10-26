---
id: method
type: constraint
summary: The project's own method rules, stated by the engineer, each with its origin and its check.
domain: conventions
last-updated: YYYY-MM-DD
related: [index]
---

# Project method

## One-liner
How we work on this project, where it refines the kit's methodology.

## Scope
Covers: rules the engineer states about how agents work here, on code or method.
Does NOT cover: preferences about a person (agent memory keeps those), or rules
that hold for every project (propose them to the kit).

## Rules

### M1: [the rule, as one imperative sentence]

[What the rule forbids or requires, and one example of a violation.]
Origin: [the engineer's words, or forebrief:<card-id>], YYYY-MM-DD.
Enforced-by: [test:<path> | mechanical:<path> | hook:<path> | none: <reason>]

## Agent notes
> When the engineer states a rule about this project, write it here in the same
> commit, not only in agent memory: memory is per machine, and other agents and
> engineers never read it. `kb-lint.py` fails a rule without `Enforced-by:`.
> A rule that recurs as a procedure can become a project skill; a rule that holds
> beyond this project goes to the kit. See `references/knowledge-base.md` in the
> spec-driven-dev skill.
