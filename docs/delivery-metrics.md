# Delivery metrics: tokens and time per accepted task

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
appends it to `kb/work/meter.jsonl`. It reads only usage numbers and timestamps.
It never reads message content. Commit the file with the task.

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

## What this does not do

There is no token budget gate. A gate rewards skipping tests and review, and the
kit values accepted quality over cost. The meter does not tell useful tokens
from wasted ones; the retrospective does. It does not price tokens. Cache
reads are cheaper than other classes, so compare classes, not only totals.
