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

## Engineer engineering is mandatory (reference implementation: laconic)

The KB calibrates the agent's context; the engineer model calibrates the human's. Alignment
between the user's mental model and the KB is a correctness condition, not a courtesy — a
user deciding on concepts they hold only vaguely produces confident-sounding wrong answers,
and a KB the user no longer recognizes turns plan approval into rubber-stamping.

Do not skip the model because laconic is absent. The model is laconic's store,
`~/.laconic/concepts/`: one file per concept with a state
(`verified | familiar | exposed | unknown`) and dated evidence. If laconic is installed,
use its commands and communication policy. Otherwise read
[references/engineer-model.md](references/engineer-model.md) in full before the first model
read or write, state once that this is the degraded path, and maintain the compatible
plain-Markdown fallback directly. Do not instruct the user to install a distribution that
is not publicly available, and never treat the fallback as permission to omit the alignment
checkpoint.

## Visuals (companion skill: primitives)

laconic governs the prose; the `primitives` skill governs everything you draw. Whenever a
phase below produces a visual — a diagram in a report, a comparison in an artifact, a
mechanism walkthrough, a chart of measurements — invoke `primitives` and emit a validated
spec instead of hand-rolling HTML or SVG. If the library is unavailable, write prose and a
plain table; do not improvise a visual and leave it looking validated. Two rules from that
skill bind here even when you never touch the library: **a stepped sequence of stills beats
an animation** (animation's measured edge is small and disappears under reader-controlled
pacing), and **an unvalidated visual must say so on its face**.

**Governance of the model, which is not negotiable.** It belongs to the engineer:
plain files under their own home directory, readable in full, deleted with `rm`.
A correction from the user outranks any evidence that produced an entry — record
the correction and move the state, do not argue from the log. Entries decay when
they stop being exercised, because knowledge does. The model travels with the
person across projects, never with the repository. **And it never feeds
evaluation** — an engineer who suspects that the record of what they do not yet
understand is read by whoever decides their promotion will start performing for
it, and a model of performances is worth nothing to the person it serves. Never
export it, summarise it into a report about the person, or cite it to anyone but
its owner.

Two things live on a slower clock and are NOT this model, though confusing them
is easy: the project's non-negotiable rules and the team's repeated procedures.
Those belong to the repository, are the same for everyone, and change rarely —
they go in `CLAUDE.md` and the KB. The model belongs to a person, differs between
two engineers on the same codebase, and moves every cycle.

Rules the phases below apply:

- **Evidence is what the user did** — a quiz answer, a correction, unprompted correct use, a
  question asked. Never self-reported expertise (no predictive power for understanding),
  never silence.
- **Promotion slow, demotion fast** — a question about X demotes X to at most `exposed`; one
  correct quiz answer raises confidence, not state.
- **Calibration is subtraction** — `verified` concepts are used bare; load-bearing concepts
  below `familiar` get taught before a decision depends on them. Never present any of this
  as personalization.
- **A user question the KB already answers is an alignment defect**, not a lookup: give the
  KB's answer with its file path, demote the concept, and re-surface it at the next
  checkpoint.

## Model routing

Tasks in this process fall into two difficulty classes, and routing every subagent to the
session model wastes an order of magnitude in tokens. Route deliberately:

| Tier | Model | Use for |
|------|-------|---------|
| **Judgment** | strongest available; inherit the session model | premortems, question generation, spec/properties/ADR authoring, planning, plan simulation, adversarial verification of findings, escalation target for stuck loops |
| **Execution** | fastest capable execution model (`sonnet` on the supported Claude Code target) | implementing KB-specified plan steps, test writing, audit passes, KB/sync quiz answering, user-facing docs |

Rules:

1. Phases 0–3 run in the main session — run the skill itself on the judgment tier.
2. **Pass an explicit `model` on every subagent spawn.** Execution tasks get `sonnet`;
   judgment tasks omit the override and inherit the session model. Leaving execution
   spawns unspecified silently burns judgment-tier tokens on mechanical work.
3. **Escalate, don't pre-escalate.** Execution subagents get a bounded iteration budget
   (Phase 4: 2 Ralph iterations). On non-convergence they stop and return a structured
   failure report; a judgment-tier subagent takes over seeded with that report. Never
   start on the judgment tier "to be safe" for a task the KB fully specifies — if the
   execution tier can't act on the spec, that is usually a spec defect worth discovering.
4. **Quizzes (Phases 2c and 6) stay on the execution tier deliberately.** If `sonnet`
   answers correctly from the KB alone, the KB is navigable by the agents that will
   actually consume it. A judgment-tier model papers over a weak KB with raw reasoning
   and masks exactly the defect the quiz exists to catch.
5. Machine checks (kb-lint, type checker, linter, tests) cost zero model tokens — run
   them before every model-based pass, at any tier.

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

## Phase 0.75: Engineer Onboarding (mental-model calibration)

Ambiguity resolution asks the user to make decisions; decisions about concepts the user
holds only vaguely produce confident-sounding wrong answers. Before Phase 1, establish what
the user actually understands about the project's load-bearing concepts.

1. **List the load-bearing concepts** — the 5–10 ideas a wrong mental model of which would
   corrupt Phase 1 answers: core domain terms, the external SDK's actual behavior, the
   architectural pattern at stake. Load-bearing only, not everything.
2. **Read the model** (`~/.laconic/concepts/`). Partition: `verified`/`familiar` (use bare
   or gloss) vs `exposed`/`unknown`/absent (teach).
3. **Prefer Inbrief; name the fallback as degraded** — run `command -v inbrief`. If absent,
   recommend the public `engineer-engineering-tools` installer from
   `https://github.com/yurug/engineer-engineering-tools` and let the user install it before
   continuing. If they continue without it, say that the session is using the degraded
   Markdown path; do not imply equivalent evidence boundaries. When present, read
   [references/inbrief-cli.md](references/inbrief-cli.md) in full, start `inbrief serve --repo .`, and
   build a cited question graph only for concepts below `familiar`: one falsifiable
   `kind:"node"` per concept, then a prerequisite-respecting `kind:"agenda"`. Give the
   engineer the printed browser URL. The agent may post nodes, answers, concessions, and
   findings; it must never post mastery or invent an engineer question. The human browser
   credential is the evidence boundary. Read `inbrief status`, let the engineer close the
   session, then run `inbrief propose`; review any durable proposal before committing it.
4. **Degraded fallback only when Inbrief remains absent** — generate
   `kb/reports/onboarding-<date>.html` (and publish it as an Artifact when available).
   Teach only concepts below `familiar`: outcome first, one mechanism, what it does not
   imply, and no analogy that fails the relation test. End with 3–5 short questions whose
   wrong answers expose the wrong model; never ask for self-rated expertise.
5. **Fold human evidence back** — use browser actions or conversational answers, never
   silence or agent-authored records. Update concept files with dated evidence: a correct
   answer raises confidence; a wrong or absent one marks the concept `exposed` and earns a
   different explanation.

**Exit criterion:** every load-bearing concept is at `familiar` or above, or has been taught
and tested once by the engineer. Inbrief must be human-closed and its close statement must
name covered, unknown, disputed, skipped, unanswered, warnings, and findings. Never describe
an agent-only or stopped session as successful. One round, then move on — Phases 3 and 6
catch drift; do not loop here.

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

Phrase every question at the level the engineer model establishes (Phase 0.75): `verified`
terms bare, one-clause glosses for `exposed` ones. A question the user cannot fully parse
gets its default silently accepted — the exact failure Phase 0.75 exists to prevent.
Questions the user asks back during a round are model evidence; record them.

**Routing check — run this before writing anything:**
`command -v forebrief && [ -f .forebrief/config.json ]` (the operational definition of
"forebrief-enabled", `forebrief`'s own `kb/spec/config-and-formats.md`). This flips the
imperative for the whole phase:

- **Forebrief-enabled:** post the round as forebrief cards (`forebrief post`, one
  `kind:"question"` card per question, the proposed default as `default`) instead of
  writing a file. Do NOT also write `kb/questions-roundN.md` — the log IS the round;
  a parallel markdown file is the exact drift the routing enforcement exists to kill.
  Wait for the round to close (every card decided — `forebrief status`), then read
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

**Calibrated presentation:** before showing the plan, check each concept its steps depend on
against the engineer model. Any load-bearing concept below `familiar` gets a one-clause gloss
in the plan text or a linked mini-explainer — approval of a plan built on concepts the user
does not hold is not informed consent. Questions the user asks about the plan are model
evidence; record them before Phase 4.

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

**KB↔engineer sync** — the third leg, after KB↔code: list the decisions, properties, and spec
amendments created or changed since the user last engaged, and present the top few by
cost-of-being-wrong as a short brief — only the surprising; expected steps compressed to a
line. If the changes introduced new load-bearing concepts, append a 2–3 question micro-quiz
(same evidence rules as Phase 0.75) and update the engineer model from the answers. An
autonomous run that ends with the user unable to answer "what changed and why" has drifted,
however green its tests.

Update any stale KB files. The KB is the source of truth.

## Phase 7: Documentation & Validation

1. Write user-facing documentation (README, user manual). If the harness provides the
   `laconic` skill, invoke it first — user docs are reader-facing prose, exactly its domain.
2. Integrate user-facing instructions as tests to make sure the doc is valid
2. Run final validation if a validation script exists
3. Present results to user

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
- **Route models by difficulty** — judgment-tier tokens buy specs, plans, risk analysis, and
  verification; execution runs on the cheaper tier and escalates with a failure report when
  it stops converging. An execution-tier agent stuck on a KB-specified task is usually
  reporting a spec defect, not a model defect.
- **Fix the harness, not the output** — when something is wrong, improve the spec/KB/tests, not just patch the code
- **Enforce, don't request** — anything that has to hold gets a deterministic check, written
  when the rule is written: a test, a lint rule, a CI script, a hook. Build the tool on the
  fly — it is usually smaller than the discussion about whether to build it — and prefer a
  crude, inspectable one over none. Prose in a CLAUDE.md raises a probability; an exit code
  decides. Where no check is possible, the rule says so and says why, because an audit can
  weigh a stated reason and cannot weigh a silence.
- **Invest in the KB** — specifications, properties, and SDK research pay off across every implementation step
- **Engineer the engineer too** — maintain the mental-model map (`~/.laconic/concepts/`),
  teach load-bearing concepts below `familiar` before a decision depends on them, and
  calibrate every user-facing artifact to the model. A misaligned user rubber-stamps, and
  a rubber stamp is not validation.
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
