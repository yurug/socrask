---
id: fixture-method-pass
type: constraint
summary: A project method rule with its origin and its channel.
domain: fixtures
last-updated: 2026-10-26
---
# Project method

## M1: No acceptance-case leak

A general rule never gains a special case that names an acceptance case.
Origin: the engineer, 2026-10-26.
Enforced-by: none: the fixture has no checker to name; a real project names `case-leak-check.py`
