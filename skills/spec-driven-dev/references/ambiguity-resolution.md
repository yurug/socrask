# Ambiguity resolution: coverage and exit

Phase 1 fails quietly in one direction: too few questions. The agent that writes
the questions also judges when none are left, its defaults read as settled, and
"the user confirms" asks the human to notice questions nobody asked. Three
mechanisms counter this; none of them proves the ledger is complete.

## The assumption ledger

Keep `kb/assumptions.md` (start from `templates/kb/assumptions.md`). One row per
choice the work depends on that neither the KB nor a human decision settles:
every proposed default, every "obviously X", every behavior picked for an edge
case. Write the row when the choice is made, not when it is asked.

- Each question in a round carries the ledger IDs it would settle.
- When a round closes, mark rows `resolved` (basis: the forebrief card or the KB
  file the decision went into) or `accepted` (the human kept the default).
- A rejected default is rewritten as the decided fact and resolved.

Check the shape at any time; run the exit gate before leaving Phase 1:

```sh
python3 tools/assumption-check.py kb/assumptions.md --exit
```

`W-empty` at exit is a prompt to look again, not a pass: zero recorded
assumptions on a non-trivial change usually means nobody wrote them down.

## The independent question pass

Each round, before posting it, spawn a fresh judgment-tier subagent. Give it the
brief (the user's request, premortem hidden assumptions, Phase 0.75 context),
the KB as it stands and the ledger, and NOT your draft questions. Ask it to walk
the demand end to end, list what it would have to guess to implement it, and
return each guess as a question with a proposed default.

Merge its questions into yours, drop duplicates, and add a ledger row for each
new guess. Report in the round how many questions came only from the independent
pass: a steady non-zero count means the main pass is under-asking.

## The stopping rule

A round in which the human overrode any default is evidence that your model of
their intent was wrong somewhere, and the same model produced the questions you
did not ask. Run another round, starting from what the overrides imply. Stop
when a round closes with no override, the independent pass adds nothing new, and
the exit gate passes.

## Slices

A slice skips KB creation, not uncertainty. Before Phase 3, list the choices the
slice needs and check each against the KB. Any choice the KB does not settle
gets a ledger row; if any row is open, run a short round on those rows only and
pass the exit gate before planning.

## Routing

Run this before writing any question.
this skill's `resolve-engineering-tool.sh forebrief` must succeed AND
`[ -f .forebrief/config.json ]` (the operational definition of
"forebrief-enabled", `forebrief`'s own `kb/spec/config-and-formats.md`). This flips the
imperative for the whole phase:

- **Forebrief-enabled:** post the round as forebrief cards (`forebrief post`, one
  `kind:"question"` card per question, the proposed default as `default`) instead of
  writing a file. Do NOT also write `kb/questions-roundN.md` — the log IS the round;
  a parallel markdown file is the exact drift the routing enforcement exists to kill.
  During a live sit-down, start the fast response sentinel from the `forebrief` skill;
  never ask the engineer to return to chat and say the round is done. Wait for the round
  to close (every card decided — `forebrief status`), then read
  `forebrief digest` for overrides/rationale before the next round. See the `forebrief`
  skill for the card/record wire shapes and the fold-in step that later lands these
  decisions in the KB.
- **Not enabled (the fallback, and the only path before forebrief exists in a
  project):** identify this as the degraded path and recommend installing/configuring the
  public `engineer-engineering-tools` suite for the next decision round. Then write all
  questions to `kb/questions-roundN.md` — do NOT present them
  inline in the conversation. After writing the file, tell the user the filename and
  the question count, then wait for them to edit the file before starting the next
  round.

## What this does not cover

- Completeness: a choice nobody noticed has no row, and no checker sees it. The
  independent pass reduces that risk; it does not remove it.
- Whether a `resolved` basis actually says what the row claims; the checker only
  verifies the reference exists.
- Direct-tier changes, which by definition carry no unsettled choice. If one
  turns up mid-change, the change was mis-sized: re-size it as a slice.
