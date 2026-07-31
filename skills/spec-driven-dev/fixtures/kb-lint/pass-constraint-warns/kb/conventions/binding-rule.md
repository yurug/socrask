---
id: fixture-conventions-pass-constraint-warns
type: constraint
summary: A binding rule outside properties/ with no channel — a warning, not an error.
domain: fixtures
last-updated: 2026-07-28
---
# Credential handling

Secrets MUST NOT be written to disk outside the keyring.

Outside `properties/` the missing channel is a warning: this is where rules
still under discussion live, and failing the build here would push authors to
stop writing them down. `--strict` promotes it for releases.
