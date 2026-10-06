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

## What this does not cover

- Completeness: a choice nobody noticed has no row, and no checker sees it. The
  independent pass reduces that risk; it does not remove it.
- Whether a `resolved` basis actually says what the row claims; the checker only
  verifies the reference exists.
- Direct-tier changes, which by definition carry no unsettled choice. If one
  turns up mid-change, the change was mis-sized: re-size it as a slice.
