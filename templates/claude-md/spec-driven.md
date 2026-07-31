# Spec-Driven Agentic Development

This project follows Spec-Driven Agentic Development. The knowledge base (`kb/`) is the source of truth. If kb/ is empty, you must build it first through ambiguity resolution.

## KB routing protocol (every task, every session — not just skill runs)

1. **Before ANY task — even one that looks trivial** — read `kb/INDEX.md` and load the
   quick-load bundle matching your task type (`kb/indexes/by-task.md`). A "simple fix"
   done without the KB is how properties get silently violated.
2. **Same-commit rule:** if your change alters behavior described in a KB file, update
   that KB file (and its `last-updated`) in the SAME commit as the code change. A KB
   updated "later" is a KB that drifts; a KB that drifts loses the agents' trust; a KB
   nobody trusts stops being maintained.
3. **If the code contradicts the KB**, stop and reconcile before building on either:
   either the KB is stale (fix it, same commit) or the code is wrong (the KB wins —
   it is the spec).
4. **Run `tools/kb-lint.py` before committing** any KB change. Lint errors are build
   failures, not suggestions. Illustrative paths in KB prose belong in code fences so
   the linter doesn't chase them.
5. **Every rule you write down carries a check.** When you add something that has to hold —
   a property, a convention, a lesson from the bug you just fixed — decide in the SAME
   commit what fails when it breaks: a test, a lint rule, a CI script, a hook. Then write
   it. Thirty lines of grep with a threshold is ordinary work, not a project, and a rule
   with no check is a rule everyone is hoping about. Properties in `kb/properties/` declare
   theirs as an `Enforced-by:` line and `tools/kb-lint.py` fails the build without one.
   Prose is not a channel: instructions raise a probability, exit codes decide. If nothing
   can check the rule, say so where the rule is written, with the reason — an audit can
   weigh a stated reason and cannot weigh a silence.
6. **Calibrate user-facing output to the engineer model** — before writing anything for
   the user (summary, plan presentation, docs), read `~/.laconic/concepts/` if present:
   use `verified` concepts bare, gloss or teach load-bearing ones below `familiar`. A
   user question the KB already answers is an alignment defect, not a lookup — answer
   from the KB with the file path, and demote the concept in the model (a question about
   X means X is not verified). The laconic plugin, if installed, enforces the
   communication policy; this rule adds the project-side loop.

## Before you start: size it, and after it fails: route it

**Size the change first.** If the diff states in one sentence AND the existing checks
already cover the behaviour it touches, run the agent and the harness and ship — the KB
routing protocol above still applies, the rest of the ceremony does not. Anything larger
gets cut into bounded changes with their own acceptance criteria before any of it starts.

**A production defect arrives with two things, and both become spec before any repair:**
a reproduction (a test that fails now — that is the acceptance criterion) and the list of
behaviours that must not change while it is fixed (named property IDs).

**When output is wrong, decide which layer broke before repairing it:**

| Wrong because… | Fix in | Not in |
|---|---|---|
| the agent ignored what the spec already said | the agent — loop again | anything else |
| the spec permitted it, or never said | the KB, first — code follows | the code alone |
| the spec said it and nothing noticed | the harness — add the check for the class | the instance alone |

Skipping that decision is how the same defect class comes back next cycle.

**The loop must ratchet.** After each iteration run
`python3 tools/ratchet.py --from-log <test output>`. It refuses a run where an obligation
that passed before no longer does, and names it. An obligation may be retired only on the
record (`--retire <ID> --reason "<why>"`). Commit `.ratchet.json`.

## Model routing (subagents)

Pass an explicit `model` on every subagent spawn; don't let execution work silently inherit
the session model.

- **Judgment tier** (session model — strongest available): premortems, spec/properties/ADR
  authoring, planning, plan simulation, adversarial verification of audit findings,
  escalation target for stuck loops.
- **Execution tier** (`sonnet`): implementing KB-specified plan steps, test writing, audit
  passes, KB quizzes, user-facing docs.
- **Escalation:** execution subagents run at most 2 Ralph iterations, then stop and return a
  failure report (failing tests verbatim, hypotheses ruled out, commits so far, suspected
  root cause, suspected spec gaps). A judgment-tier subagent continues from that report —
  7 iterations total per step, then split the step. A spec gap found this way is fixed in
  the KB, not just in code.
- **KB quizzes stay on the execution tier:** the KB must be navigable by the agents that
  will actually consume it; a stronger model masks navigability defects.
- Machine checks (kb-lint, type checker, linter, tests) cost zero model tokens — run them
  before every model-based pass.

## Project-specific rules

Keep this file limited to non-negotiable rules and repeated procedures that must be
present in every session. Put specifications, properties, decisions, external-system
research, implementation plans, and detailed conventions in the routed KB instead of
repeating them here. The `spec-driven-dev` skill owns the methodology; this file owns
only the project's persistent routing and policy.
