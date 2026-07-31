# Implementation and quality audits

Read this reference in full before executing Phase 4 or Phase 5.

## Contents

- [Phase 4: Implementation](#phase-4-implementation-ralph-loops)
- [The loop must ratchet](#the-loop-must-ratchet-or-it-wanders)
- [Repair or resample](#repair-or-resample)
- [Phase 5: Quality Audits](#phase-5-quality-audits)

## Phase 4: Implementation (Ralph Loops)

For each step in the plan:

### Ralph Loop (max 7 iterations per step across both tiers; if not converging, stop and split the step)

Ralph Loop is the iteration shell; the fresh subagent is the clean-context mechanism. Use both:
spawn ONE fresh subagent per step (not per iteration — the same subagent runs the iterations
within a step so it accumulates context about the failure modes it just fixed).

### The loop must ratchet, or it wanders

Iterating until green is not enough. A loop that re-runs everything and reports
pass/fail can lose ground it already held and never notice — a test suite passing
on one version says nothing about the next one, a repair can break what worked an
hour ago. **What makes a loop climb is a ratchet, and it is false by default: all
four of these are engineered, none is free.**

1. **The work splits into obligations checkable on their own.** That is what the
   property IDs are for. A step whose acceptance criteria cannot be checked
   independently is a step that was never sized (Phase 0); go back and cut it.
2. **An obligation that passed stays passed when its neighbours move.** Run
   `ratchet.py --from-log <test output>` after every iteration. It refuses a run
   where a previously-passing obligation has vanished, and names it. Commit
   `.ratchet.json` — an uncommitted high-water mark ratchets nothing.
3. **The checker says WHICH obligation failed, not that something did.** This is
   why test names start with the property ID. A test suite that reports "17 failed"
   gives the next iteration nothing to aim at, and imprecise feedback — not the
   number of turns — is where repair loops are measured to fail.
4. **A repair cannot quietly undo the rest.** An obligation may legitimately
   disappear (merged, superseded, scope cut), but only on the record:
   `ratchet.py --retire <ID> --reason "<why>"`. A silent drop fails the run.

Modular proof developments get all four by construction, because a kernel
rechecks what depends on what. Everywhere else this is a target you build toward,
and the four above are the concrete form of building toward it.

### Repair or resample

Repairing on feedback is the default here, and it is a choice rather than a
settled result — repeated sampling with the checks picking the survivor has not
been shown worse. Repair is right in this setting for two reasons: the feedback
is nearly free (the checks already say what failed and where), and a repaired
change arrives with a history a human can read, which matters when a human signs
it. **Resample instead when the checks are cheap to run and the candidates are
small** — spawn N independent attempts at the same step and keep whichever
survives the harness. Nothing else in the loop moves; the acceptance criterion is
the same either way, and it must not come from whatever generated the candidate.

One caveat bounds both: iteration only pays where a single attempt has
non-trivial probability of success, and an imperfect checker caps the whole
thing at a level no amount of extra iteration lifts. If the loop is not
converging, the checks are the first suspect, not the model.

**Tiered execution:** spawn the step's subagent on the execution tier (`model: sonnet`) with a
budget of 2 Ralph iterations. Green within budget: done. Not green: the subagent stops (it does
NOT keep thrashing past its budget) and returns the failure report below; the main session then
spawns a fresh judgment-tier subagent seeded with that report plus the original contract, which
continues the loop up to the shared 7-iteration cap. Escalation loses the execution agent's
working memory — the failure report is the entire handoff, so it must be specific enough that
the judgment agent does not re-explore ruled-out dead ends.

**Subagent contract:**
- Inputs in the prompt: the full step text from `kb/plan.md`; pointer to `kb/INDEX.md` and
  `kb/indexes/by-task.md#implement`; property IDs to satisfy (e.g. "enforce P3, P7, P12");
  acceptance criteria; the iteration budget (2 on the execution tier; the remaining cap after
  escalation); this Phase 4 section so it can run the loop itself.
- Returns on success: commit hash(es) produced; test results (pass/fail counts, names of any
  failures); any KB drift it noticed (file + line + expected-vs-found); any unresolved ambiguities.
- Returns on budget exhaustion — the failure report: failing test names with verbatim error
  output; each hypothesis tried and why it was ruled out; commits produced so far; suspected
  root cause; KB files consulted and any suspected spec gap. A spec gap surfaced here is fixed
  in the KB (fix the harness, not the output) before or alongside the escalation.

**Understand:**
- Read `kb/INDEX.md` -> follow `kb/indexes/by-task.md#implement`
- Read `kb/external/` for SDK behavior constraints
- Identify relevant properties from `kb/properties/`
- Evaluate the ambiguities and uncertainties of the implementation task, refine the task expectations if any.
- **Identify the riskiest piece of THIS step** — the one sub-task whose failure would
  invalidate the rest of the step (an unknown SDK behavior, an unproven algorithm, a
  performance-critical inner loop, a concurrency assumption). Name it explicitly. This
  is what gets implemented and validated FIRST, even if it is harder or less fun than
  the surrounding scaffolding. Do not warm up on easy code while the scary part waits.

**Implement with literate and test-driven-development style:**
- Attack the riskiest piece identified above FIRST. The first red/green test pair must
  pin down that uncertainty (e.g. "the SDK actually paginates the way we assumed",
  "the algorithm terminates on this adversarial input"). If the riskiest piece turns out
  to be impossible or much harder than expected, surface it now and re-plan — that is
  exactly the discovery this ordering exists to force early.
- Start with failing tests that surface the gap and the properties to enforce, comment them with WHY,
  and commit them as a red baseline — the next (green) commit then shows exactly what made them pass.
- File header: module purpose, spec references, key design decisions
- Every public function: JSDoc with @param (meaning), @returns, @throws, @invariant P<N>
- Every conditional whose why is not obvious from the surrounding code: WHY comment
- Every algorithm step: WHAT comment
- Every magic value: explained
- DI everywhere, no `any`, functions < 30 lines, files < 200 lines
- **Use explanation length as a cohesion signal.** Explain each changed module's purpose in
  one sentence without joining independent responsibilities with “and”. If that requires
  multiple unrelated clauses, split the module or record the invariant that makes those
  responsibilities one concept. Treat a failed explanation test as design feedback, not as
  a request for a longer comment.

**Write comprehensive tests:**
- Unit tests (mocked deps), integration tests, edge-case tests (T-entries), error-path tests
- Property-based and fuzzing-based tests for critical invariants (randomized inputs)
- Test names start with property reference: `"P4: roundtrip preserves fields"`
- At least one test per function
- Mutation testing to improve quality of tests

**Validate:**
- Type checker passes
- All tests pass
- Linter clean
- `ratchet.py --from-log <test output>` holds or advances — a regression here is a
  failure of this iteration even when every other check is green

**Self-audit:**
- Comment ratio is a smoke alarm, never a target: a file under ~30% is a signal to check for
  missing WHYs, not a number to write toward — padding toward a quota is the defect this rule
  exists to prevent. Never write a comment that restates the code. Explain the WHY, and the
  WHAT that is not obvious from the source. Be pedagogical, imagine you are writing a textbook
  or a blogpost about the code you are explaining.
- Every public function has complete doc in the ecosystem standard format
- Every type definition has complete doc in the ecosystem standard format
- Every non-obvious conditional has a WHY comment

**Iterate** until green, then commit and move to next step.

## Phase 5: Quality Audits

After implementation is complete, run these audits — one fresh subagent per audit type so each
keeps an independent perspective, all on the execution tier (`model: sonnet`). Prefer the
`Workflow` tool when the harness provides it: each audit dimension pipelines straight into
per-finding verification with no barrier, and each stage carries its own model override.
Otherwise spawn all audit subagents IN PARALLEL with the Agent tool (they are read-only
analyses of the same code; sequential spawning wastes time and lets earlier findings anchor
later ones):

1. **Test gap analysis**: for each feature/property/edge-case — is it tested? Write missing tests to get full code coverage.
2. **Security**: credentials, input validation, data exposure, injection risks
3. **Performance**: API call efficiency (check against kb/external/ request budgets), pagination, async patterns
4. **UX**: error messages, help text, progress indicators, exit codes
5. **Spec compliance**: for each spec item, does the code match?
6. **Simplicity and cohesion**: could we get to the same result with a more compact and
   direct approach, and can each changed component's purpose be explained without joining
   independent responsibilities with “and”?
7. **Provability**: is there a property from `kb/properties/` that explains why this change is correct?

**Auditors have a stopping rule.** Flag what affects correctness or a stated
requirement; stay quiet about the rest. An auditor that comments on everything
trains the reader to skip its comments, and then it catches nothing — a finding
that is true but touches neither correctness nor a stated requirement costs more
attention than it returns. Taste, naming preferences, and "I would have done it
differently" are not findings. If a dimension produces no finding that clears
that bar, it reports none; an empty audit is a valid result.

Write findings to `kb/reports/`.

**Adversarial verification before fixing:** for each CRITICAL or HIGH finding, spawn a fresh
skeptic subagent on the judgment tier whose job is to REFUTE it (with the finding, the relevant
code, and the KB). Verification is where plausible-but-wrong findings must die, so it is the one
Phase 5 stage that earns judgment-tier tokens. Findings that survive refutation are real;
refuted ones are dropped with a one-line rationale in the report. This prevents the fix loop
from churning on plausible-but-wrong findings.

Workflow sketch (adjust dimensions and schemas per project; the verify stage omits the model
override so it inherits the judgment-tier session model):

```js
const audits = await pipeline(
  DIMENSIONS,                     // the 7 audit types above, one prompt each
  d => agent(d.prompt, {model: 'sonnet', phase: 'Audit', schema: FINDINGS}),
  r => parallel(r.findings.filter(isCriticalOrHigh).map(f => () =>
    agent(refutePrompt(f), {phase: 'Verify', schema: VERDICT})
      .then(v => ({...f, verdict: v})))))
```

Fix all critical and high issues that survived verification. Fixes run on the execution tier —
a verified finding plus the KB is a full spec for the fix — with the Phase 4 escalation rule if
a fix does not converge.

**A verified finding whose class can recur leaves a check behind, not just a fix.** The fix
closes this instance; the check closes the class. Write it in the same commit — a test
naming the property, a lint rule, a CI grep — and if the finding revealed a property nobody
had stated, state it in `kb/properties/` with that check as its `Enforced-by:` channel. An
audit that only ever fixes instances re-finds the same class next round, and pays
judgment-tier tokens each time to rediscover it.

**Ralph Loop** (max 7 iterations): audit -> fix -> re-audit until 0 criticals; remaining highs
must be either fixed or documented in `kb/reports/` with a rationale. If the loop is not
converging, stop and return to Phase 3 to split the slice.
