# Delivery metrics: tokens, time and tool calls per accepted task

The kit measures cost per accepted task, including repair and review. Two
numbers matter: the tokens a task consumed, and the time from its start to its
accepted outcome. Each one only counts next to the quality signals. A cheap
task that a user rejects is not cheap.

## Measure

The coordinator marks each ledger task:

```sh
python3 tools/task-meter.py start T-12 --tier slice --budget 200k
# ... the work, subagents included ...
python3 tools/task-meter.py stop T-12
```

`stop` adds up the usage that the host recorded between the two marks and
appends it to `kb/work/meter.jsonl`. It also counts the tool calls and their
errors, and the runs and failures of each harness script under `tools/` or
`skills/<skill>/` that the agent ran. It reads usage numbers, timestamps, tool
names and error flags. From a shell command it keeps only the script name. It
never reads other message content. Commit the file with the task.

- **Claude Code**: the meter uses `$CLAUDE_CODE_SESSION_ID`. It counts that
  session and its subagents, and each API request once.
- **Codex**: it has no session ID in the environment. The meter counts the
  messages whose working directory is the one where `start` ran. Give each
  concurrent agent its own worktree (`tools/agent-work.py`).
- A task that spans several sessions gets one `start`/`stop` pair per session.
- `--budget` copies the plan step's optional `Budget:` field. The report shows
  the ratio, so estimates improve over time.

## Report

```sh
python3 tools/task-meter.py report --check
```

Per task, the report gives:
- tokens by class: input, cache read, cache write and output;
- active time (gaps over five minutes do not count) and wall-clock time;
- budget against actual;
- tool calls and errors, and the failed runs of each harness script;
- from `kb/work/ledger.json`: the first observed result, the number of failed
  observations, and the time to acceptance.

A task whose total is more than twice the median of its tier is an outlier. The
median needs three or more earlier tasks in that tier.

## Act on it

1. Put the meter line for each task in the Backbrief or handoff, beside the
   quality signals.
2. Write a retrospective for each outlier: the cause, and one change to the
   harness or the KB that removes it.
   `task-meter.py note T-12 --retro "re-read sync code; fix: add kb/models/sync.md"`.
   `report --check` fails while an outlier has no retrospective.
3. Look for the usual causes first:
   - a KB gap that sends the agent into the code;
   - a judgment step given to the execution tier;
   - a loop that repairs without new evidence;
   - a context that grew without need.

## Retrospective at each milestone

A task retrospective explains one outlier. The milestone retrospective looks at
the harness itself: which checks fail often, which tools error, where the agent
repairs without new evidence. It runs at each completed milestone.

1. Record each local gate result. A local CI runner calls, per gate:
   `python3 tools/retro.py record <gate> --exit <code> --seconds <s>`.
   The journal is `<git common dir>/socrask/checks.jsonl`. It is per clone and
   not versioned, and it also holds the gates that ran outside an agent session.
2. When the milestone's tasks are closed, write the numbers:
   `python3 tools/retro.py draft P1/M2 --write`. The file in `kb/work/retros/`
   gives first-attempt acceptance, repair loops, tokens per task against the
   previous milestone, tool errors, and the failure rate of each harness script
   and gate.
3. With the engineer, write one finding per signal worth acting on, with its
   cause. Give each finding a disposition: `change:` and the commit, task or KB
   file that acts on it; `reject:` and the reason; or `kit:` when the change
   holds beyond the project. If nothing is worth acting on, write
   `No findings: <reason>`.
4. Set `retrospective` on the milestone in the ledger. `retro.py check` runs in
   CI. It fails on a completed milestone without a retrospective, and on a
   finding without a disposition.

Read a high failure rate before you act on it. A check that fails often can
catch real defects, or it can show a KB gap or an unclear instruction. A check
that never fails can still be needed.

## What this does not do

There is no token budget gate. A gate rewards skipping tests and review, and the
kit values accepted quality over cost. The meter does not tell useful tokens
from wasted ones; the retrospective does. It does not price tokens. Cache
reads are cheaper than other classes, so compare classes, not only totals.
Gates that run only in a remote CI do not reach the journal. A failed command
that runs two harness scripts counts a failure for both.
