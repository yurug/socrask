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

- **The task's root.** In Claude Code, the meter uses `$CLAUDE_CODE_SESSION_ID`.
  Elsewhere, the root is the Claude Code session or the Codex thread that ran
  `task-meter.py start <TASK>`. Run `start` from the agent session that does the
  work, never from another terminal. The working directory decides nothing: a
  Codex session rooted at the repository runs its commands in worktrees.
- **The task's agents.** The meter counts the root and its subagents, each API
  request once, by runtime, model and role. The role is the subagent type in
  Claude Code (`reviewer`, `general-purpose`), and in Codex the agent's role or
  path (`tree_review`), or `guardian` for its safety reviews. Codex runs other
  providers too: the model reads `openrouter/google/gemini-3-pro`, for example.
- **No silent zero.** A `stop` that finds no request records the task as
  unmeasured and exits 1. `task-meter.py remeasure` measures the unmeasured stops
  again while the transcripts still exist, and rewrites them in place.
- **Shared roots.** Two tasks that run at once in one root share its requests.
  The report says "window shared with"; give each concurrent task its own agent
  session to separate them.
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

## The whole history

`insights.py` reads the meter and the ledger, archive included, and answers
"which agent, at what cost, for which result":

```sh
python3 tools/insights.py --check
```

- **Agents:** requests, tokens and cost by runtime, model and role.
- **Outcomes:** per lead model and tier, first-attempt acceptance, repair loops,
  median tokens, cost and active time.
- **Periods:** per iteration (or ISO week), acceptance, tokens, cycle time from
  first start to first acceptance, and the ratios of actual to budget and to
  `estimate_hours`.
- **Hints:** a tier where a cheaper lead model has enough judged tasks and a
  first-attempt rate within 10 points of the best one. A hint is a trial to run
  under [model routing](../skills/spec-driven-dev/references/model-routing.md),
  not a decision.

Costs need `kb/work/prices.json`, in dollars per million tokens by model
substring. `--check` fails when more than 10% of the last 20 metered tasks are
unmeasured: an analysis of missing data misleads.

## Retrospective at each milestone and iteration

A task retrospective explains one outlier. The milestone or iteration
retrospective looks at the harness itself: which checks fail often, which tools
error, which agents spend the tokens, where the agent repairs without new
evidence. It runs at each completed milestone, and at the end of each iteration
(`retro.py draft I-3 --write`).

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
   file that acts on it, with the metric it should move (`metric: first-attempt`,
   `tokens:slice`, `active-time`, `repair-loops`, `tool-errors:<tool>`,
   `script:<name>`). The next retrospective of the same kind shows that metric
   then and now, so a change that did not help is seen; `reject:` and the reason; or `kit:` when the change
   holds beyond the project. Ask also which operation the agents did by hand
   more than once: its change is a tool ([deterministic tools](../skills/spec-driven-dev/references/deterministic-tools.md)).
   If nothing is worth acting on, write `No findings: <reason>`.
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
