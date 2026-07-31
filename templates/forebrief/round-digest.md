---
id: {{id}}
type: decision
summary: {{summary}}
domain: {{domain}}
tags: [record, fold-in]
last-updated: {{date}}
forebrief-record: {{record_ids}}
---
# {{title}}

Folded from forebrief round `{{round_id}}` (posted {{posted_at}}) via
`forebrief fold`. Every card below shows its CURRENT record (the
highest-seq decision or reconciliation -- forebrief's append-only
resolution rule, P5) with its full rationale history and ask-why thread
verbatim.

{{cards}}
## Related files

- `.forebrief/decisions.jsonl` -- the source-of-truth log this digest was
  folded from; every `seq` referenced above resolves there.
