---
id: fixture-props-pass-structural-proof
type: constraint
summary: Structural and proof channels, one with its trust boundary named and one without.
domain: fixtures
last-updated: 2026-07-28
---
# Functional properties

## P1: A closed account cannot be debited

The type makes it unrepresentable: `debit` takes an `OpenAccount`, and the only
way to obtain one is a constructor that rejects closed accounts.

Enforced-by: structural:src/account.ts

## P2: The balance never goes negative

Enforced-by: proof:proofs/balance.v
Trusted: the proof is over the reference model, not the extracted OCaml; the
extraction and the Rocq kernel are assumed correct, and the arithmetic is
unbounded where the runtime's is 63-bit.

## NF1: A full reconciliation is linear in the ledger size

This one deliberately omits the trust boundary, so the fixture keeps a live
example of what W-trust catches.

Enforced-by: proof:proofs/complexity.v
