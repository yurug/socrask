---
id: decisions-round-1
type: decision
summary: Fixture -- verbatim rationale and thread, wrapped and quoted.
domain: forebrief
tags: [record, fold-in]
last-updated: 2026-07-24
forebrief-record: [card-a]
---
# Decisions -- round 1

## Card 1: Does decision.mode keep the value "reconciled"?

**Chosen:** Remove it

**Rationale:**

> Removing reconciled mode avoids two representations of one
> state.

**Thread:**

- ask_why: "Why remove it instead of keeping it unused?"
- answer: An unused enum value invites a second producer eventually;
  removing it is safer.
