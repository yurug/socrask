# Roadmap for complex projects

A slice plan (`kb/plan.md`) covers three or four steps. A project that needs more
than one slice, or any Full-tier work, also needs a roadmap. The engineer must
see it and approve it before work starts. The roadmap answers three questions:
which outcomes come in which order, how the work runs in parallel, and what can
make the execution fail.

## Build it

The data lives in the ledger, on the project, as `roadmap` (schema in
`tools/roadmap-check.py`). Start `kb/roadmap.md` from `templates/kb/roadmap.md`.

1. **Milestones.** Each milestone is an accepted, observable outcome with
   acceptance cases, never "code done". Each milestone lists the risks it retires.
2. **Schedule.** Give every task its `depends_on` and an `estimate_hours` in
   agent-hours. The tool computes the parallel waves and the critical path.
   Maximize throughput on the critical path: start its tasks first. Give the
   other agents off-path work, within the project's `wip_limit`.
3. **Execution risks.** For each risk, give probability, impact, the task that
   retires it, and the tasks it blocks. Retire uncertainty first: a spike or a
   prototype comes before any work that depends on the answer. A high risk's
   spike starts in the first wave, with no dependency.
4. **Narrative.** In `kb/roadmap.md`, explain why this order, and how each
   uncertainty is retired. Then generate the tables:

```sh
python3 tools/roadmap-check.py --write
```

## Consult the engineer

The engineer validates the roadmap; the agent does not approve its own plan.

1. Present it before the first slice starts. Show the milestones as a rail and
   the waves as lanes, with `primitives`, plus the risk table. Lead with the
   critical path and the biggest risk.
2. Ask through a forebrief card: approve, or change a named milestone, order or
   risk. Each option states what it changes in the roadmap.
3. Record the approval in the ledger with the digest that the engineer saw:

```sh
python3 tools/roadmap-check.py --digest PR-1
```

   Set `approval` to `human-complete`, that digest, and the evidence reference
   (`forebrief:<card-id>`). Without a human answer, the approval stays `pending`.
   `degraded-authorized` needs the engineer's explicit authorization.
4. Present it again at each milestone, with the milestone's architecture review
   (`architecture_review` on the milestone), and whenever the roadmap changes. A
   changed roadmap changes the digest, and `roadmap-check.py` then fails until
   the engineer approves the new version.

## Gate

`roadmap-check.py` runs in CI. It fails in these cases:
- work has started without a current approval;
- blocked work does not follow its spike;
- the dependencies contain a cycle;
- a milestone has no acceptance cases;
- the generated tables are stale.

It does not check that the estimates are right or that the risk list is
complete. `task-meter.py` gives the actual hours to calibrate the estimates;
the premortem on the plan finds missing risks.
