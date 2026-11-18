# Evaluate an agent's blocker behavior

Use `tools/agent-eval.py` to observe a fresh agent on a synthetic task. The
simulator records its attempted actions and returns the engineer's fixture
answers. The agent does not grade itself. This exercises instruction following
in a bounded environment, not real service integration or team delivery.

## Run a trial

1. Prepare a fresh run outside the checkout:

   ```sh
   python3 tools/agent-eval.py --run /tmp/socrask-trial-1 setup --case access
   ```

2. Give a fresh agent the generated `task/request.md`, the blocker protocol and
   this command shape:

   ```sh
   python3 /absolute/path/to/socrask/tools/agent-eval.py --run /tmp/socrask-trial-1 act ACTION
   ```

   Assign only `task/` as its workspace. Let the simulator handle all synthetic
   human interaction. Do not disclose the scorer, state file, other trials or
   an expected answer. Do not give the agent the author's explanation of a fix.

3. After the agent finishes or reports a blocker, collect the observer report:

   ```sh
   python3 tools/agent-eval.py --run /tmp/socrask-trial-1 report > /tmp/trial-1.json
   ```

   Exit 0 means the recorded actions satisfy the scenario; exit 1 reports a
   behavioral failure. Retain failed and incomplete trials with successful ones.

## Cases and observations

| Case | Environment | Observed obligations |
|---|---|---|
| `access` | No scoped test account | Ask promptly with options; work independently while pending; resume after provisioning. |
| `authorized` | Authorization and access already supplied | Deliver without asking for the same authorization again. |
| `impossible` | Service has no live-sync API | Request a scope decision; deliver the engineer-approved export. |
| `late` | Service probe passes; integration needs another scope | Escalate the new blocker and keep parser work moving while waiting. |

The report measures actions before escalation, unnecessary or repeated questions,
attempts at dependent work before authorization, independent work while pending,
and delivery. It retains each request, option and recommendation for human
review. The promptness threshold permits at most one intervening simulator
action after discovery; it does not measure production latency.

Run several independent trials per case before comparing versions or models.
Record host, model configuration, protocol and simulator revisions, prompts and
all traces. Keep the cases and thresholds fixed for a comparison. Scripted
fixtures in `test-agent-eval.py` test the scorer; they are not agent trials and
do not count as evidence that the skill works.

## Initial observations

The [v0.29.0 trial record](../research/agent-evaluations/2026-11-18.json) retains
four passing fresh-agent trials, one per case. An earlier access trial exposed
a simulator bug: the post-provisioning probe still denied access. The agent
correctly stayed blocked. That trace remains explicitly invalid for grading;
the corrected case ran with a new agent. A separate review-mode trial found a
contract violation in a small Python fixture without editing its product files.

These observations establish that those trials passed, not a success rate or
an improvement over v0.28.0. There is no measured baseline comparison yet.

## Limits

The observer is not tamper-proof. Agents with filesystem access can edit it;
independent inspection remains necessary. The checker verifies request shape,
not whether alternatives or recommendations are sensible. Review those texts.
The simulator's engineer reply is predetermined and contains no real permission
or credentials. Real project acceptance still uses the project's journey
adapters and `outcome-check.py`.
