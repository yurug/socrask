---
id: adr-002-per-repo-log
type: decision
summary: Fixture -- rationale verbatim, thread represented by a forebrief:record link.
domain: forebrief
tags: [record, fold-in]
last-updated: 2026-07-24
forebrief-record: card-b
---
# ADR-002 — Per-repo decision log

## Context

Should the log be per-repo or per-session?

## Decision

Per-repo `decisions.jsonl`.

## Consequences

One log survives every session.

## Rationale exchange

One log per repo, not per session, because forebrief needs cross-session
provenance backbrief never required.

The full ask-why exchange runs long; see forebrief:record:2 in
`.forebrief/decisions.jsonl` for the complete thread.

## What this does not cover

Nothing else.
