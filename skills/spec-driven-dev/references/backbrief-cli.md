# Backbrief command-line reference

Backbrief opens a grounded comprehension session after a change. The agent builds a cited
map of what changed; only the engineer can advance understanding in the browser.

After installing the public engineer-engineering toolsuite, invoke commands as
`backbrief …`.

| Command | Does |
|---|---|
| `backbrief serve [--repo DIR] [--focus diff:FROM..TO\|component:PATH\|system] [--title T] [--port N] [--open]` | Starts a local session and prints its URL, tokens, port, session id, and PID. |
| `backbrief act FILE.json` / `backbrief act -` | Posts an agent-authored map action, answer, finding, or KB proposal and prints citation validation. |
| `backbrief events [--since N] [--follow] [--timeout SECS] [--actor human]` | Streams the human's annotations, responses, and findings as JSONL. |
| `backbrief status` | Reports the session state, URL, and whether agent and human have engaged. |
| `backbrief digest` | Prints cross-session coverage, open questions and findings, and recently understood ground. |
| `backbrief stop` | Ends the session and flushes its digest without inventing human understanding. |

Exit `0` from `act` means every citation validated. Exit `2` means the action was posted
with one or more citations visibly flagged as unverified; repair the citation rather than
treating it as grounded. Exit `1` is a malformed action, missing server, or transport error.

## Contents

- [Payloads accepted by `act`](#payloads-accepted-by-act)
- [Scope the checkpoint](#scope-the-checkpoint)
- [Final diff and evidence](#final-diff-and-evidence)

## Payloads accepted by `act`

Backbrief uses `type`, `payload`, and `refs`, not Inbrief's `kind`/`node` shape.
First upsert the grounded map, then present one node. Adapt these illustrative
citation paths and lines to actual repository evidence:

```json
{
  "type": "map_upsert",
  "refs": [],
  "payload": {
    "nodes": [{
      "id": "recovery-order",
      "type": "mechanism",
      "level": "mechanism",
      "question": "How is saved state restored?",
      "answer": "Saved records are replayed in order; an incomplete final record is ignored.",
      "citations": [{"kind":"code","path":"src/log.ts","startLine":20,"endLine":45}],
      "requires": []
    }]
  }
}
```

```json
{
  "type": "present_move",
  "refs": [],
  "payload": {
    "nodeId": "recovery-order",
    "say": "Recovery follows the saved order. The final incomplete record does not alter restored state.",
    "ask": {"kind":"calibration","text":"Is this recovery rule clear, or does it need evidence?"}
  }
}
```

Map questions are limited to 12 words, answers to 30, with at least one valid
citation and acyclic, resolving `requires`. Map node types are `concept`,
`mechanism`, `property`, `boundary`, `rationale`, or `quirk`; levels are `system`,
`subsystem`, `mechanism`, or `code`. A broken map citation rejects the upsert;
it is not the flagged-but-posted behavior of ordinary cards.

A move's `say` is limited to 25 words, `ask.text` to 15. The question/answer come
from its map node; do not repeat them as new move fields. A pure calibration move
can omit `device`; explanatory devices use Backbrief's own device schema, not an
Inbrief primitive copied verbatim. Optional `intent` is limited to 30 words.
Inspect the response and post a single valid map node before submitting a batch.
`clientKey`, if supplied for replay safety, must be a valid ULID; reusing the
triggering event's ULID is appropriate for one reaction, not several distinct ones.

## Scope the checkpoint

- Use `diff:FROM..TO` for the normal per-cycle checkpoint.
- Use `component:PATH` when onboarding an engineer onto one subsystem.
- Use `system` only for a genuinely small repository.

Read `backbrief digest` before resuming a repository. Revisit invalidated citations first,
then the current frontier. While the browser is open, assign a fast, low-cost subagent as
the response sentinel when the host supports subagents. It repeatedly runs `backbrief
events --actor human --since <lastCommittedSeq> --follow --timeout 20`, relays every
envelope to the main agent in sequence order, and advances its cursor only after the main
agent has reacted or explicitly acknowledged it. The main agent drains this inbox before
its next move, before stopping, and before its final answer. Without subagents, the main
agent runs the same loop itself.

Derive `clientKey` for a reaction from the triggering envelope id. That makes replay safe
if the listener crashes after posting the reaction but before committing its cursor. The
sentinel never invents human input or resolves a contested explanation.

Backbrief runtime files and credentials live under `.backbrief/` and must remain ignored.
The server binds to `127.0.0.1`. Never post `got-it`, mastery, or another human-only action
from the agent credential.

## Final diff and evidence

The coordinator owns a single checkpoint after integrating worker output, KB,
documentation, and final validation. Resolve the base and head to full commit
hashes and use `--focus diff:BASE..HEAD` with those exact hashes. A later edit
requires an updated diff and checkpoint; do not reuse completion for an older head.
The map explains the behavior change, why it exists, validation, consequences,
and open questions with resolving citations. Keep the first view concise.

Mark the alignment record `pending` when launching. `status` exposes presence
(`humanSeen`), not comprehension. Read actual substantive human events and clear
contested explanations before recording `human-complete` with session/event
references. Never manufacture human-only actions, closure, or quiz answers.
If unavailable or declined, record explicit human authorization before using
`degraded-authorized`; state the limitation in the final result. A sent URL,
ignored prompt, or stopped server remains pending. See `docs/alignment.md`.
