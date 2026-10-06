---
id: assumptions
type: decision
summary: Every choice the agent made that neither the KB nor a human decision settles; Phase 1 exits when none is open.
domain: meta
last-updated: YYYY-MM-DD
related: [index]
---

# Assumption ledger

Checked by `assumption-check.py` (spec-driven-dev). `--exit` fails while any row is `open`.

- `open`: not settled. Becomes a question in the next round.
- `resolved`: Basis is `forebrief:<card-id>` or the KB file where the decision now lives.
  A rejected default is rewritten as the decided fact and resolved, not deleted.
- `accepted`: the human kept the default as is. Basis: `accepted by <who> <YYYY-MM-DD>`.

| ID | Assumption | Status | Basis |
|----|------------|--------|-------|
| A1 | [A choice the agent would otherwise make silently] | open | |
