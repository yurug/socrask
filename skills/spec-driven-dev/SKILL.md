---
name: spec-driven-dev
description: "Run spec-driven agentic development from ambiguity resolution through an agent-optimized knowledge base, ratcheted implementation loops, quality audits, and engineer alignment. Use when starting a project or major feature, adopting the methodology in an existing repository, or continuing work in a repository that already uses its KB and harness; re-invocation sizes direct, slice, full, and production-defect paths."
---

# Spec-Driven Agentic Development

Build software the right way: spec before code, knowledge base before implementation,
validation at every step. This skill runs the full methodology end-to-end.

## Tooling note

"Ralph Loop" refers to the `ralph-loop` plugin, installable as
`ralph-loop@claude-plugins-official`. When available, start it with
`/ralph-loop:ralph-loop` before an implementation or audit cycle and cancel it with
`/ralph-loop:cancel-ralph` when done. When unavailable, execute the same bounded
generate-check-decide loop manually; the plugin is an interface, not the mechanism.

## Human alignment and concise communication

Forebrief captures decisions; Inbrief prepares a human for a meaningful decision;
Backbrief explains the actual resulting change. None substitutes for another.
The coordinator owns these checkpoints for the whole slice; child agents return
findings and evidence without opening sessions or prompting the user independently.

Apply laconic's communication discipline even when its plugin is unavailable:
lead with the outcome or decision, give only the context needed to act, identify
material uncertainty, and offer detail progressively. For a decision, state the
options, recommendation, consequence, and what answer is needed. For a result,
state what changed, why, validation, and remaining limits. Concise does not mean
omitting an unresolved question or an important risk.

An engineer model is optional and private. Read or update persistent personal
concept records only when the owner has opted in; otherwise use the current
conversation to explain unfamiliar terms. Read
[references/engineer-model.md](references/engineer-model.md) before using a model.
A question may be a request for evidence, a challenge, or a scope clarification:
**never demote knowledge merely because the user asks a question**, including
one answered by the KB. Answer it with the relevant source and repair unclear
explanations. Silence and agent-written quizzes are not human evidence.

## Recorded checkpoints (every task)

Create an alignment record when claiming work, before implementation; see
`docs/alignment.md` for the schema and `tools/alignment-check.py` for the gate.
Record the tier and exact base commit. Inbrief is required for a new subsystem,
unfamiliar load-bearing concept, or decision whose meaning needs explanation.
A Slice on familiar ground may mark it `not-required` with a concrete reason.
Full work normally requires Inbrief. Backbrief is required for every non-Direct
change. A Direct change records why both are unnecessary and still receives a
short result summary. Reassess the tier if scope grows.

Run the checker at start and finish. `required` and `pending` are unfinished;
`human-complete` cites actual human event evidence for the checkpoint;
`degraded-authorized` cites explicit human authorization to use a limited or
skipped checkpoint and remains visibly degraded. Tool absence, a launched browser,
a sent URL, a stopped server, green tests, or time passing never imply completion.
Record session/event references only, never credentials or a personal profile.
At finish pin the exact reviewed head; any later diff invalidates that Backbrief.
The check verifies record consistency, not human understanding or evidence authenticity.

## Visuals (companion skill: primitives)

For a visual, invoke `primitives` and use a validated spec. If unavailable, use
prose and a plain table; label any unvalidated visual explicitly. Prefer a
reader-paced sequence of stills when explaining steps.

## Model routing

Choose models by demonstrated outcome quality, task risk and allowed data processing.
Cost is measured per accepted task, including repair and review, not per token alone:

| Tier | Model | Use for |
|------|-------|---------|
| **Judgment** | strongest available; inherit the session model | premortems, question generation, spec/properties/ADR authoring, planning, plan simulation, adversarial verification of findings, escalation target for stuck loops |
| **Execution** | a model already validated for this bounded task class | routine implementation, mechanical transformations, KB navigation checks |

Rules:

1. Phases 0–3 run in the main session — run the skill itself on the judgment tier.
2. Select a supported execution model explicitly when the host exposes that choice;
   `sonnet` is the Claude example, not a portable model name. Judgment tasks inherit
   the session model. If routing is unavailable, state that once and use the host default.
3. **Establish a capable reference before optimizing cost.** Use judgment capability
   for unfamiliar integration, acceptance design and consequential repairs, even with
   a written spec. A weaker model's failure does not prove the spec is wrong. Execution
   agents get at most two unsuccessful iterations before a structured handoff; repeated
   failures require a changed hypothesis. Preserve the shared seven-iteration ceiling.
4. **Test KB navigation with the agents that consume it.** Keep that diagnostic
   separate from product acceptance. For product agents, record the effective model
   of every decision-making helper, not just the model selected in the chat UI.
5. Machine checks (kb-lint, type checker, linter, tests) cost zero model tokens — run
   them before every model-based pass, at any tier.

## User outcome quality

For product behavior or a recurring user defect, read
[outcome acceptance](../../docs/outcome-quality.md). Preserve the original feedback,
representative starting state, observable result and non-regression cases. A passing
code suite, a deployed artifact and accepted user behavior are separate evidence.
Run `tools/outcome-check.py` on complete, version-bound reports before promotion;
missing/skipped cases and stale evidence never count as validation. Keep first attempts
separate from retries. Register the gate in the real delivery command, not only a runbook.
When the project has no adapter yet, report that gap and implement one bounded journey
first; do not fabricate outcomes from unit-test totals. Select review dimensions by risk.
After a kit upgrade, follow [agent adoption](../../docs/agent-adoption.md): publication,
installation, acknowledgement and demonstrated use are distinct states.

## Preliminary remark

The work lives in the **meaning-to-specification gap**: turn what the team means into
properties a machine can check without pretending that passing checks proves the meaning was
right. Humans own meaning; the harness owns repeatable correctness against the stated spec.

Run this process iteratively, one feature (or small set) at a time, producing a working
product at the end of each iteration cycle. Iteration is not optional — the more we can
decompose work into tasks with a clear definition of done, the better. On re-invocation,
Phase 0 detects existing artifacts and skips phases that already passed.

## Phase 0: Orient

Determine the current state before doing anything:

1. Check if `kb/INDEX.md` exists. If yes, read it — the project has a KB already. Skip to the phase that matches the current state (Phase 3 if KB exists but no plan, Phase 4 if plan exists but code is incomplete).
2. Check if there's a `CLAUDE.md` with project-specific instructions. If yes, follow those — they override this skill's defaults.
3. If starting from zero, confirm with the user: "I'll follow the spec-driven process: resolve ambiguities, build a knowledge base, plan, then implement. Ready?"

### Size the demand before running any of it

**Not every change deserves this ceremony, and pretending otherwise is how a
methodology gets abandoned on exactly the changes it was meant to protect.**
Decide the tier first, out loud, in one line:

- **Direct** — the diff states in one sentence AND the existing checks already
  cover the behaviour it touches. Run the agent, run the harness, ship. Update
  the KB only if behaviour described there changed (the same-commit rule still
  binds). Do not open Phase 1.
- **Slice** — one bounded change with its own acceptance criteria, on ground the
  KB already covers. Phases 3–6, skipping KB creation.
- **Full** — new project, new subsystem, or a change whose meaning is not settled.
  Everything from Phase 0.5.

A demand that is not one bounded change gets **cut into changes that are**, each
carrying its own acceptance criteria, before any of them reaches the agent.
Sizing is the step that is easy to skip and expensive to skip: an unsized demand
is what produces a plan whose steps cannot be checked independently, which is
the thing that later prevents the Phase 4 ratchet from holding.

### The second door: a production defect

A defect enters better dressed than a feature request, and it enters here, not
at Phase 4. Before anything is repaired, it must arrive with two things, and
both become spec:

1. **A reproduction** — the failing input, as a test that fails now. That test
   is the acceptance criterion.
2. **The behaviours that must not change while it is fixed** — named as existing
   property IDs. That list is what the ratchet holds during the repair.

A defect whose reproduction nobody can write is not ready to fix; it is ready to
investigate, and the investigation's output is the reproduction. Fixing code
that reproduces nothing produces a change nothing can validate.

## Phase 0.5: Premortem the Idea

Before sinking time into ambiguity resolution and the KB, pressure-test the idea itself.
The premortem flips Claude out of agreeable mode: instead of asking "is this a good idea?",
we assume it already failed 6 months from now and work backward to find why. This produces
honest, specific blind spots in minutes — cheap to surface now, expensive to discover at
Phase 4.

**How to run it:**

1. Invoke the `premortem` skill on the user's idea as stated. Pass whatever context exists
   (the user's pitch, any attached files, the project `CLAUDE.md`).
2. The premortem skill handles its own minimum-context gate (what / who / success criteria).
   If the idea is too vague to premortem, run one quick Phase 1 round first for just enough
   concreteness, then return here.
3. Save the report and transcript inside `kb/reports/` (e.g. `kb/reports/premortem-idea-<timestamp>.html`
   and `.md`) so they live alongside other quality artifacts and are reachable from KB indexes later.

**What to do with the output:**

- **Hidden assumptions** become forced questions in the next Phase 1 round.
- **The most dangerous failure** becomes a property in `kb/properties/` (the system must prevent it)
  or an explicit out-of-scope item in `kb/domain/prd.md`.
- **The revised plan / pre-launch checklist** seeds the acceptance criteria for Phase 3 steps.
- If a failure mode is fatal (no realistic mitigation), surface it to the user before continuing.
  The premortem can kill or pivot an idea — that is a successful outcome, not a failed phase.

**Exit criterion:** the user has seen the premortem findings and either (a) confirmed proceed,
(b) revised the idea, or (c) abandoned it. Do not slide into Phase 1 if (c).

## Phase 0.75: Inbrief when understanding affects the decision

1. Name the few load-bearing concepts needed for the next decision. Use the
   conversation and repository evidence, without unsolicited personal profiling.
2. Resolve Inbrief with `resolve-engineering-tool.sh inbrief`; use its printed
   absolute path. Read [references/inbrief-cli.md](references/inbrief-cli.md).
   Start a grounded session, post cited nodes and an agenda, and share its URL.
3. Mark the checkpoint `pending`. Process human events and answer questions;
   only the human may supply mastery or human closure evidence. An agent-authored
   close record does not establish human completion.
4. Close the record only from actual human evidence. If unavailable or declined,
   explain the limitation and obtain explicit authorization for a concise
   conversational briefing or a skipped checkpoint. Cite that authorization as
   `degraded-authorized`; never call it tool-backed human completion.

Teach only what the decision needs. A short explanation and a concrete question
are usually enough; do not impose a quiz on an already clear, familiar task.
Independent preparation can proceed while a checkpoint is pending, but do not
make dependent decisions until it is settled. Installation is optional; use the
reference's install instructions when requested rather than blocking on setup.

## Phase 1: Ambiguity Resolution

Before writing ANY code, eliminate all blind spots.

**Generate questions grouped by topic:**
- Features and scope (what does it do, what does it NOT do)
- Data model (entities, fields, constraints, formats)
- Algorithms and logic (sync semantics, conflict resolution, state machines)
- External integrations (APIs, SDKs — their ACTUAL runtime behavior)
- Error handling (what can fail, what the user sees)
- Security (credentials, input validation, data exposure)
- UX (CLI flags, output format, progress indicators)
- Edge cases (empty inputs, large inputs, unicode, concurrent access)

**For each question, propose a default answer** based on best judgment. Format:

```
**N. [Question]**
Default: [Proposed answer]
```

Phrase questions using the context established in Phase 0.75; gloss unfamiliar
load-bearing terms. Clarification is welcome and never automatically changes a
personal knowledge rating. Defaults still need the applicable human decision.

**Routing check — run this before writing anything:**
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

Iterate until no ambiguities remain.

**Exit criterion:** User confirms all ambiguities resolved.

## Phase 2: Knowledge Base Creation

**Before executing Phase 2, read [references/knowledge-base.md](references/knowledge-base.md)
in full.** It defines the directory shape, ordered file construction, enforcement-channel
vocabulary, KB audit loop, mandatory usage harness, and exit criterion.

## Phase 3: Planning

Read [project control](../../docs/project-management.md) when maintaining plans or
handling feedback. Keep one `kb/work/ledger.json`: project → plan → task → original
request, with owner, next action, review date, dependencies and acceptance cases.
Reopen repeated failures; preserve previous evidence. Reconcile every declared
feedback/backlog source, limit active work, and run `tools/project-check.py` in the
real CI/handoff path. Imported uncertainty stays visible; code completion never
closes product acceptance. Review blocked, overdue and unverified work each session.

Create `kb/plan.md` — incremental implementation plan:
- 3-4 implementation steps maximum (not counting quality audit). If you need more, the slice
  is too large — close this invocation after one slice and re-run the skill for the next.
- **Every step names the obligations it must satisfy** (property IDs) and the ones it must
  not break. That list is what the Phase 4 ratchet holds; a step whose obligations cannot
  be checked independently is a step that was never sized.
- **VERTICAL SLICE FIRST, THROUGH THE RISKIEST PATH**: Step 1 MUST produce a minimal but
  RUNNING program, AND that slice must traverse the riskiest/most-uncertain part of the
  system — not the easiest happy path. If the project's hardest question is "can we
  actually sync against this flaky external API?", step 1's running skeleton calls that
  API. Do not pick a comfortable slice that postpones the scary part.
  For a CLI: entry point, commands registered, basic happy path works end-to-end.
  Do NOT spend step 1 on foundations only (types, errors, config) without commands.
  A running skeleton with basic commands is more valuable than perfect types with no commands.
- **Order steps by risk and blocker status, NOT by ease.** The first step is the one whose
  failure would invalidate the most downstream work — typically the highest-uncertainty
  piece, the integration with an unknown external dependency, or the hardest algorithmic
  question. Easy/peripheral work (polish, secondary commands, nice-to-haves) goes last.
  If you catch yourself proposing an "easy warm-up step" before the hard one, that is the
  failure mode this rule exists to prevent — re-order.
- Subsequent steps add depth: more commands, edge cases, error handling, quality
- Each step: modules, relevant properties, acceptance criteria
- Each step must produce observable progress (new command, new behavior)
- For each step, name the **single biggest unknown** ("what if X doesn't work?") in the
  step's acceptance criteria. Phase 4 will prove that piece works first.

**Plan-simulation gate:** before showing the plan to the user, spawn a fresh subagent with the
plan and the KB. Ask it to walk each step end-to-end, list ambiguities and uncertainties, and
generate questions for the user. Resolve every question before exit.

**Plan premortem:** for plans with high cost-of-being-wrong (irreversible data shapes,
public APIs, multi-week slices), re-run the `premortem` skill on the plan itself. The Phase 0.5
premortem stress-tested the idea; this one stress-tests the implementation strategy. Save the
report in `kb/reports/premortem-plan-<timestamp>.{html,md}` and fold its checklist items into
the plan's acceptance criteria.

**Calibrated presentation:** use the conversation context to gloss unfamiliar
load-bearing concepts before asking for a decision. Consult a persistent engineer
model only if its owner opted in. Answer questions with relevant sources; do not
infer ignorance or automatically record a knowledge rating from a question.

**Exit criterion:** User approves the plan.

## Phase 4–5: Implementation and Quality Audits

**Before executing Phase 4 or Phase 5, read
[references/implementation-and-audits.md](references/implementation-and-audits.md) in full.**
It defines the bounded Ralph Loop, ratchet, repair-versus-resample decision, implementation
standards, auditor fan-out, adversarial verification, and stopping rules.

## Phase 6: KB Sync

After implementation, verify the KB still matches reality. Run `python3 tools/kb-lint.py kb`
first — its W-stale warnings (file committed after its `last-updated`) are the mechanical
drift signal; fix every error and triage every warning. Then check what the machine cannot:
- Does architecture doc match actual module structure?
- Do spec files cover all implemented features?
- Do properties cover all enforced invariants?
- Does external/ accurately reflect SDK usage?
- Are cross-references valid?
- Write 3 hard questions about the recent changes to `kb/reports/sync-quiz.md`, then have fresh
  execution-tier (`sonnet`) subagents with KB-only access answer them — one per question, fanned
  out (Model routing rule 4 applies). Update the KB to close any gap.

**Backbrief covers the final aggregate diff for every non-Direct change.**
Finish code, KB, documentation, and validation first, then resolve Backbrief with
`resolve-engineering-tool.sh backbrief` and read
[references/backbrief-cli.md](references/backbrief-cli.md). Read its digest,
pin the slice's base and final head, and build a cited map of what changed, why,
validation, consequences, and unresolved questions. All child results enter this
single coordinator-owned checkpoint. Give the engineer the URL and process human
events. A URL, `humanSeen`, or `backbrief stop` is not evidence of comprehension.
Mark `human-complete` only from substantive human checkpoint evidence with no
unresolved contested explanation. Otherwise leave `pending`, or cite explicit
human authorization as `degraded-authorized`. Report that distinction plainly.

The degraded conversational brief follows the same concise structure and names
its limitation. Do not invent answers or force a comprehension quiz for familiar
material. Any edits after review require a refreshed diff and checkpoint.
Run `tools/alignment-check.py` at finish before claiming the workflow complete.

Update any stale KB files. The KB is the source of truth.

## Phase 7: Documentation & Validation

1. Write user-facing documentation (README, user manual). If the harness provides the
   `laconic` skill, invoke it first — user docs are reader-facing prose, exactly its domain.
2. Integrate user-facing instructions as tests to make sure the doc is valid
2. Run final validation if a validation script exists
3. Complete the final aggregate Backbrief described in Phase 6 after these changes,
   then present results and the recorded checkpoint status to the user

## Route every failure to the layer that owns it

When the output is wrong, the first decision is not how to fix it but **which
layer broke**. Three answers, and picking one is mandatory before any repair:

| The output is wrong because… | Route to | What you change |
|---|---|---|
| the agent produced something the spec already ruled out | **the agent** | run the loop again (repair or resample); change nothing else |
| the spec permitted it, or never said | **the specification** | close the KB gap first, then re-run — the fix is a KB commit, and the code follows |
| the spec said it and nothing noticed | **the harness** | add the check that would have caught this class, then fix the instance |

A loop with no routing degenerates into retry-until-green, and retry-until-green
converges on plausible rather than on correct. The tell: the same class of defect
reappearing in a later cycle means an earlier failure was routed to the agent
when it belonged to the spec or the harness.

## The harness must stay explainable

**If you cannot explain to a new engineer what the harness checks, the harness is
too complex.** A harness with hundreds of checks and layers of meta-checking
becomes its own engineering problem: the next failure looks exactly like one of
its own bugs, and the team starts debugging the harness instead of the agent.

Keep an inventory — one line per check, saying what it refuses — and hold it to a
line budget (this kit keeps `docs/harness.md` under 60 lines, enforced by
`tools/harness-inventory.sh`). When the inventory stops fitting, retire checks
rather than raising the budget. Two kinds of simplicity are in play and only one
of them is about size: what must be auditable is the **theorem and the
specification** (what was proved, what the team wants), never the proof. A proof
can be ten thousand lines of tactics; that is the verifier's problem. The
specification being unreadable is yours.

Stupidly simple, not simplistic: some systems are intrinsically complex, and
nothing here says every system should be small. The claim is narrower — within
the scope where this process runs end to end, a human can read the specification,
the harness, and the result, and say what each one claims, catches, and lets
through.

## What this process does not cover

Shipping ends this loop, not the story. Telemetry, a rollback that works, and a
deploy small enough to reason about are the operations practice this process
**assumes and does not replace** — if they are absent, no amount of spec rigour
upstream makes a release safe, and that gap is out of scope here rather than
solved here. What the change does in production comes back as the next demand,
through Phase 0's second door.

On a slower cadence, turn the process on itself, because a process nobody
questions converges fast to the wrong place. Three questions, none of which any
single check answers: is the harness still simple and auditable, or has it become
its own engineering problem? Is the artifact still the right artifact? Where
would an unknown-unknown enter, and which auditor would catch it?

## Principles to maintain throughout

- **Tackle uncertainty and blockers first** — within any plan, step,
  or single coding session, the hardest, most uncertain, or blocking
  work goes FIRST. Don't take arbitrary choices that may have
  observable changes, ask the user. Easy and peripheral work
  waits. Deferring risk feels productive (visible progress on safe
  code) but it is how projects discover at the last minute that a core
  assumption was wrong, after everything around it has already been
  built. If you notice yourself reaching for the comfortable task
  while a scary one waits, stop and switch. The scary one is the task.
- **Premortem before you build** — challenge the idea (Phase 0.5) and the plan (Phase 3) by assuming they already failed; blind spots are cheaper to find here than in code
- **Route models by demonstrated quality** — use capable judgment for uncertain integration,
  acceptance and consequential repairs. Optimize cost only after task-class validation;
  investigate model, specification, context and tool limitations as competing causes.
- **Fix the harness, not the output** — when something is wrong, improve the spec/KB/tests, not just patch the code
- **Enforce, don't request** — anything that has to hold gets a deterministic check, written
  when the rule is written: a test, a lint rule, a CI script, a hook. Build the tool on the
  fly — it is usually smaller than the discussion about whether to build it — and prefer a
  crude, inspectable one over none. Prose in a CLAUDE.md raises a probability; an exit code
  decides. Where no check is possible, the rule says so and says why, because an audit can
  weigh a stated reason and cannot weigh a silence.
- **Invest in the KB** — specifications, properties, and SDK research pay off across every implementation step
- **Keep the human aligned** — explain load-bearing concepts before decisions and
  the actual diff before completion. Record real human evidence or explicit
  degraded authorization; personal profiling is optional.
- **Agent navigation** — every KB file must be self-sufficient and link to what's next
- **External deps are dangerous** — always research actual runtime behavior before implementing
- **Ralph Loops converge — if they ratchet** — implement -> validate -> fix -> repeat
  climbs only when what passed stays passed, the checker names which obligation
  broke, and no repair silently undoes another. Without those, the same loop wanders.
- **Match the ceremony to the change** — a one-sentence diff the checks already
  cover gets the agent and the harness, nothing else. A methodology with no cheap
  path gets abandoned on the cheap changes, which are most of them.
- **Prefer unrepresentable to caught** — a type, an opaque constructor, or a
  capability that makes the wrong answer impossible to express beats a test that
  catches it afterwards, and a proof beats both for a critical core — as long as
  what the proof does not cover is written down beside it.
- **Route the failure before fixing it** — agent, specification, or harness; a
  repair applied without that decision is how a defect class comes back next cycle.
- **Keep the harness explainable** — if a new engineer cannot be told what it
  checks, it has become the thing you are debugging.
