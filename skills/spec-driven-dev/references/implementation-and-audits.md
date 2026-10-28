# Implementation and quality audits

Read this reference in full before executing Phase 4 or Phase 5.

## Contents

- [Phase 4: Implementation](#phase-4-implementation-ralph-loops)
- [The loop must ratchet](#the-loop-must-ratchet-or-it-wanders)
- [Repair or resample](#repair-or-resample)
- [Phase 5: Quality Audits](#phase-5-quality-audits)

## Phase 4: Implementation (Ralph Loops)

Before implementation, pass the alignment start gate (see `docs/alignment.md`).
The coordinator owns the checkpoint record and all human briefings; subagents
return findings for one final aggregate Backbrief and never prompt independently.
Ratchet input is complete version-1 structured test results, not log text; see
`docs/ratchet.md` for the adapter contract.

For each step in the plan:

### Ralph Loop (max 7 iterations per step across both tiers; if not converging, stop and split the step)

Ralph Loop is the iteration shell. Delegate when independent work and host authorization
make it useful; a single agent may run the same loop. When delegating, use one agent per
bounded step so it retains the evidence from its unsuccessful hypotheses.

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
   `ratchet.py --from-results <results.json>` after every iteration. It refuses a run
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
converging, investigate the checker, model capability, available context and tool interface
as competing hypotheses; a written specification does not rule out model weakness.

**Tiered execution:** use a capable reference for unfamiliar integration, acceptance design
and consequential repairs. A cheaper execution tier is appropriate after demonstrated
quality on that task class. Bound its unsuccessful attempts at two, then hand off the
failure report with the original contract. Preserve the shared seven-iteration cap.
Any receiving agent needs enough evidence not to repeat ruled-out hypotheses. Passing
unit checks establishes implementation evidence; behavioral acceptance still needs the
observed user outcome described in `docs/outcome-quality.md`.

**Subagent contract:**
- Inputs in the prompt: the full step text from `kb/plan.md`; pointer to `kb/INDEX.md` and
  `kb/indexes/by-task.md#implement`; property IDs to satisfy (e.g. "enforce P3, P7, P12");
  acceptance criteria; the iteration budget (2 on the execution tier; the remaining cap after
  escalation); this Phase 4 section so it can run the loop itself. Dispatch on the step's
  `Tier:` field; only a step that passes `plan-check.py` goes to the execution tier.
- Execution-tier agents do not settle choices. A choice the step leaves open, or a
  `Hand off` condition, ends the attempt with the failure report below, and the planner
  fixes the step.
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
- Read the step's `Proof:` sketch and the cited `kb/models/` file. Keep the design rules
  of [proof-ready design](proof-ready-design.md). If the code needs an argument the sketch
  does not give, stop and fix the sketch and the model, in the same commit as the code.
- Evaluate the ambiguities and uncertainties of the implementation task, refine the task expectations if any.
- **Identify the riskiest piece of THIS step** — the one sub-task whose failure would
  invalidate the rest of the step (an unknown SDK behavior, an unproven algorithm, a
  performance-critical inner loop, a concurrency assumption). Name it explicitly. This
  is what gets implemented and validated FIRST, even if it is harder or less fun than
  the surrounding scaffolding. Do not warm up on easy code while the scary part waits.

**Garden before you change.** Make the change easy, then make the easy change. Before
editing a file, read it against the code rules below: cohesion, local comprehension, the
literate level, and the unit tests. If the file fails them in the part you are about to
change, improve it first:
1. If the module's contract has no unit tests, write characterization tests: they pin
   what the code does today, so the refactoring can be checked.
2. Refactor or rewrite without changing behavior: merge or split along the cohesion
   tests, rewrite the header and comments so the file reads cold, rename, remove dead
   code. All tests stay green and the ratchet holds.
3. Commit this as its own commit (`garden: <file>: <what improved>`), before the
   commit that changes behavior. A reviewer then reads a pure refactoring, then a
   small change.

Scope and budget: garden only the files the step touches, and only as much as the change
needs to be clear and safe. Spend at most about as much effort as the change itself. If
the file needs more (a redesign, a new interface, a change other modules see), do not
start it here. Record it as a roadmap item with the finding, and tell the engineer.
A kernel declared in `critical-core.md` is gardened only on the judgment tier, with
human review, like any other change to it.

**Implement with literate and test-driven-development style:**
- Attack the riskiest piece identified above FIRST. The first red/green test pair must
  pin down that uncertainty (e.g. "the SDK actually paginates the way we assumed",
  "the algorithm terminates on this adversarial input"). If the riskiest piece turns out
  to be impossible or much harder than expected, surface it now and re-plan — that is
  exactly the discovery this ordering exists to force early.
- Start with failing tests that surface the gap and the properties to enforce, comment them with WHY,
  and commit them as a red baseline — the next (green) commit then shows exactly what made them pass.
- Follow [component design](component-design.md): general and composable, DRY, information
  hiding, de Bruijn kernels, minimal state, precise types, least authority, determinism,
  versioned data, structured logs. DI where a dependency must be replaced in a test, no `any`.

**Code rules.** The reader is an engineer who opens one source file. They have not read the
KB, the spec, the plan or this session. Write for them.

1. **Cohesion decides the boundaries, not size.** Apply the split and merge tests of
   [component design](component-design.md#the-principles). Do not create a file for a
   type, a constant, or a helper with one user: put it beside its user. Size is a review
   trigger in both directions. A file over ~400 lines or a function over ~50 lines states
   why it is one concept (a parser, a state machine or a test table can be). A new file
   under ~50 lines with one caller states which decision it hides from that caller.
   If a module's purpose is hard to say in one sentence, change the design; do not
   write a longer comment.
2. **Local comprehension.** The file alone is enough to understand why it exists and how
   it works.
   - A KB reference is a pointer for more detail, never a replacement for the
     explanation. Write the claim in words, then the reference:
     `// The cursor never decreases, so a retry never emits an event twice (P4).`
     A comment that only says `// enforces P4` or `// per ADR-007` is a defect.
   - Use plain words, or define a project term on its first use in the file. No
     session, plan or review labels (step numbers, slice names, finding IDs).
   - Describe the code as it is now, not its history ("new approach", "fixed",
     "now handles"). History goes in the commit message.
   - At a call whose correctness depends on a property of the callee, state that
     property at the call site. Do not write "see foo.ts".
3. **Literate at the right level.** Explain the idea before the details, as a textbook
   section does.
   - The file header gives the problem the module solves, the approach (the key idea,
     the data representation, and why it was chosen over the obvious alternative), the
     invariants it keeps, and what it does not do. For a tricky module, add a short
     worked example.
   - Each public function documents its contract in the ecosystem's format: the
     meaning of each parameter, the result, the errors, the preconditions. Write
     invariants in words, with the property ID after them.
   - Inside a non-trivial algorithm, comments name its phases and say why each one is
     needed. Do not comment each line, and never write a comment that restates the
     next line.
   - Every non-obvious conditional gets a WHY comment. Every magic value is explained.
   - Order the file for a reader, where the language allows it: the central type and
     the entry point first, the helpers after.
4. **Unit tests for each module's contract.** Each module has unit tests that call its
   interface directly, without the rest of the system. An acceptance test or an
   end-to-end test does not replace them. Each case of the contract has a test: each
   kind of result, each error, each boundary value. Read together, the test file is an
   executable description of the module. When an integration test finds a defect,
   add a unit test in the module where the defect is.

**Write comprehensive tests:**
- Unit tests for each changed module's contract (rule 4 above), then integration tests,
  edge-case tests (T-entries), error-path tests
- Property-based and fuzzing-based tests for critical invariants (randomized inputs)
- Test names start with property reference: `"P4: roundtrip preserves fields"`
- Each invariant the step's proof sketch cites gets a property-based test named by its ID:
  `"I2: cursor never decreases"`
- At least one test per function
- Mutation testing to improve quality of tests

**No case leak:** never make a general rule specific so that an acceptance case passes.
A branch on the case's name, a fixture, or a value copied from its data makes the case
pass and prove nothing. When the general rule cannot pass the case, stop and report: the
rule or the case is wrong, and the engineer decides which. `case-leak-check.py` refuses
production code that names a declared case; the review covers the forms it cannot see.

**Validate:**
- Type checker passes
- All tests pass
- Linter clean
- `ratchet.py --from-results <results.json>` holds or advances — a regression here is a
  failure of this iteration even when every other check is green

**Self-audit:**
- Comment ratio is a smoke alarm, never a target: a file under ~30% is a signal to check for
  missing WHYs, not a number to write toward — padding toward a quota is the defect this rule
  exists to prevent. Never write a comment that restates the code. Explain the WHY, and the
  WHAT that is not obvious from the source. Be pedagogical, imagine you are writing a textbook
  or a blogpost about the code you are explaining.
- Every public function and type has complete doc in the ecosystem standard format
- Every non-obvious conditional has a WHY comment
- Reread each changed file as a stranger: remove every comment that needs the KB to make
  sense, or complete it in words

**Iterate** until green, then commit and move to next step.

## Phase 5: Quality Audits

After implementation, select the relevant dimensions below from the changed risks.
Use an independent perspective for consequential acceptance or trust-boundary changes,
with a model capable of adversarial judgment. Give the reviewer the original request,
contract and artifacts before the author's explanation. Delegate independent read-only
reviews when authorized and useful; seven parallel agents are not a quality criterion.

1. **Test gap analysis**: for each feature/property/edge-case — is it tested? Write missing tests to get full code coverage.
2. **Security**: credentials, input validation, data exposure, injection risks
3. **Performance**: API call efficiency (check against kb/external/ request budgets), pagination, async patterns
4. **UX**: error messages, help text, progress indicators, exit codes
5. **Spec compliance**: for each spec item, does the code match?
6. **Simplicity and cohesion**: could we get to the same result with a more compact and
   direct approach? Does each changed component pass the split and merge tests of
   [component design](component-design.md#the-principles)?
7. **Provability**: is there a property from `kb/properties/` that explains why this change is correct?
8. **Component design**: the review questions in [component design](component-design.md#review-questions).
9. **Cold read**: give a fresh reviewer each changed file alone, without the KB, the task
   or the author's explanation. Ask what problem the file solves, how it works, why this
   approach, and what breaks if its main invariant fails. Each wrong or missing answer is
   a finding, located where the reader got lost. This is the check for code rules 2 and 3;
   the author cannot run it, because the author cannot forget the KB.

**Auditors have a stopping rule.** Flag what affects correctness or a stated
requirement; stay quiet about the rest. An auditor that comments on everything
trains the reader to skip its comments, and then it catches nothing — a finding
that is true but touches neither correctness nor a stated requirement costs more
attention than it returns. Taste, naming preferences, and "I would have done it
differently" are not findings. If a dimension produces no finding that clears
that bar, it reports none; an empty audit is a valid result.

Write findings to `kb/reports/`.

**Adversarial verification before fixing:** try to refute consequential findings against
the code, contract and a reproduction. Use a fresh capable reviewer when authorized and
useful. Record what was demonstrated and what remains hypothetical; surviving one review
is not proof. Drop refuted findings with their evidence instead of creating churn.

Workflow sketch (adjust dimensions and schemas per project; the verify stage omits the model
override so it inherits the judgment-tier session model):

```js
const audits = await pipeline(
  SELECTED_DIMENSIONS,             // chosen from the risks of this change
  d => agent(d.prompt, {phase: 'Audit', schema: FINDINGS}),
  r => parallel(r.findings.filter(isCriticalOrHigh).map(f => () =>
    agent(refutePrompt(f), {phase: 'Verify', schema: VERDICT})
      .then(v => ({...f, verdict: v})))))
```

Fix critical and high issues that survived verification. Select the repair model by
consequence and demonstrated task capability; a verified finding does not make a complex
repair routine. Retain the Phase 4 bounded iteration and structured failure handoff.

**A verified finding whose class can recur leaves a check behind, not just a fix.** The fix
closes this instance; the check closes the class. Write it in the same commit — a test
naming the property, a lint rule, a CI grep — and if the finding revealed a property nobody
had stated, state it in `kb/properties/` with that check as its `Enforced-by:` channel. An
audit that only ever fixes instances re-finds the same class next round, and pays
judgment-tier tokens each time to rediscover it.

**Ralph Loop** (max 7 iterations): audit -> fix -> re-audit until 0 criticals; remaining highs
must be either fixed or documented in `kb/reports/` with a rationale. If the loop is not
converging, stop and return to Phase 3 to split the slice.
