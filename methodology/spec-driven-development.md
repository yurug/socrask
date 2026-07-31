# Spec-Driven Agentic Development

## The Problem

Most teams using AI agents are putting a motor on a bicycle. They give an agent a prompt
and expect working software. The agent produces plausible code — it compiles, it looks
reasonable — but it doesn't work correctly because the agent was never told what "correct"
means.

## The Four Pillars

Software development in the age of AI agents requires four disciplines:

### 1. Software Engineering
Design, architecture, execution, validation, code quality, continuous delivery, formal
methods. This hasn't changed — agents still need to produce software that meets engineering
standards. Structure pays twice because it shapes both maintenance and the next agent's
input. Use explanation length as a cohesion signal: a component whose purpose needs several
independent clauses probably contains several concepts and should be split unless one
invariant genuinely binds them.

### 2. Harness Engineering
An agent is a stochastic process. The harness constrains it:
- **CLAUDE.md** — the system prompt for your project (with the KB routing protocol on top)
- **Skills** — reusable procedures the agent can invoke
- **Ralph Loops that ratchet** — implement -> validate -> fix -> repeat converges only
  if progress is kept. A ratchet is four engineered properties, false by default: work
  splits into independently checkable obligations; an obligation that passed stays
  passed when its neighbours move; the checker names *which* one failed; and a repair
  cannot silently undo the rest. `ratchet.py` holds the second and fourth. Without
  them the loop wanders, and iterating without checking buys nothing.
- **Routing** — when output is wrong, decide which layer broke before repairing: the
  agent (loop again), the specification (close the KB gap, code follows), or the
  harness (add the check that would have caught the class). A loop with no routing
  degenerates into retry-until-green, which converges on plausible, not on correct.
- **Proportionality** — a one-sentence diff already covered by the checks gets the
  agent and the harness, nothing more. A process with no cheap path is abandoned on
  the cheap changes.
- **An explainable harness** — if a new engineer cannot be told what it checks, it has
  become its own engineering problem. Keep an inventory under a line budget, and
  retire checks rather than raise the budget.
- **Feedback scripts** — capture actual errors, feed them back verbatim
- **Mechanical validation** — every rule you write down carries a channel, and choosing it
  is part of writing the rule. There are three, in decreasing reliability: *presence*
  (injected into every session — a SessionStart hook, CLAUDE.md), *instruction* (prose the
  agent may or may not follow — compliance decays exactly on the tasks that look trivial),
  and *mechanical* (a script whose exit code fails the build). A rule that could be
  mechanical and is left instructional is a defect, not a style choice. kb-lint in
  pre-commit/CI is what turns "the KB is maintained" from a hope into an exit code, and the
  same move is available for almost anything else you want held: build the checker when the
  rule is written, not later. Thirty lines of grep with a threshold is ordinary work.
  When a rule genuinely resists checking, say so *in* the rule with a stated reason, so the
  next audit reads the reason instead of assuming coverage.
- **Model routing** — token spend is a harness parameter, not an accident. Judgment-tier
  models (the strongest available) handle specs, plans, risk analysis, and adversarial
  verification; execution-tier models handle well-specified implementation, audits, and
  KB quizzes, with a bounded iteration budget and escalation to the judgment tier — via
  a structured failure report — on non-convergence.

The harness is what makes the agent's output converge on correctness instead of
plausibility.

### 3. Knowledge Engineering
The knowledge base is the foundation that every implementation step builds on. It's designed for agent
navigation — precise context, few tokens, few hops:
- **Self-sufficient files** — understand each in isolation
- **Routing tables** (INDEX.md, by-task.md) — "given my task, what do I load?"
- **Many small files** — agents can selectively load; can't selectively ignore
- **Cross-references** (Agent notes, Related files) — guide toward files you didn't know you needed
- **One register per file; define once** — procedure files give steps, decision files give
  rationale, never blended; terms are defined in the glossary and nowhere else
- **External dependency research** — document actual SDK runtime behavior before implementing

### 4. Engineer Engineering
The symmetric discipline to knowledge engineering: the KB calibrates the agent's context,
the engineer model calibrates the human's. The process maintains a per-user map of
demonstrated understanding (laconic's `~/.laconic/concepts/`, states `unknown` →
`verified`, every claim backed by dated evidence — never self-report, never silence) and
uses it to teach load-bearing concepts *before* decisions depend on them, phrase questions
and plans at the right abstraction level, and treat a user question the KB already answers
as an alignment defect. A misaligned user rubber-stamps, and a rubber stamp is not
validation.

## The Methodology

### Phase 0: Orient, and size the demand
Detect existing artifacts (`kb/INDEX.md`, `CLAUDE.md`, prior plan) and skip phases that
already passed. Re-invocation is the common case; starting from zero is the rare one.
Then pick the tier out loud: **direct** (one-sentence diff the checks already cover — run
the agent and the harness, nothing else), **slice** (one bounded change on covered ground),
or **full**. A demand that is not one bounded change gets cut into ones that are, each
with its own acceptance criteria, before it reaches the agent. A production defect enters
by a second door, carrying a reproduction and the list of behaviours that must not change
while it is fixed; both become spec before anything is repaired.

### Phase 0.5: Premortem the Idea
Before sinking time into ambiguity resolution and the KB, pressure-test the idea itself.
Assume it has already failed 6 months from now and work backward to find every reason why.
This flips the agent out of agreeable mode and surfaces honest, specific blind spots in
minutes — cheap to discover here, expensive to discover at Phase 4. The premortem can
kill or pivot an idea, and that is a successful outcome, not a failed phase. Output feeds
forced questions into Phase 1, properties into Phase 2, and acceptance criteria into Phase 3.

### Phase 0.75: Engineer Onboarding
Before asking the user to decide anything, establish what they actually understand about
the project's load-bearing concepts. Read the engineer model, teach what sits below
`familiar` with a pedagogical HTML brief ending in a 3–5 question self-quiz (answers are
performance evidence; self-assessment is not), and fold the answers back into the model.
Phase 1 questions, the Phase 3 plan, and the Phase 6 sync brief are then written at the
level the model establishes.

The model and alignment checkpoint are mandatory. `laconic` is their reference
implementation; `inbrief` and `forebrief` are the reference interaction mechanisms. When a
tool is unavailable, use the documented plain-file fallback and call it degraded: the
fallback preserves the activity, not the tool-enforced human credential or append-only log.

### Phase 1: Ambiguity Resolution
Generate questions, propose defaults, iterate with the human. Exit when no blind spots
remain. The cost of one extra question round is negligible; the cost of a wrong assumption
is architectural rework.

### Phase 2: Knowledge Base Creation
Build the KB following the agent-optimized structure. This is the longest phase and the
most important one — everything downstream depends on it.

### Phase 3: Planning
Incremental steps, each traceable to properties and acceptance criteria. 3-4 steps max,
ordered by risk: the first step is a vertical slice through the riskiest path, not the
easiest happy path. For plans with high cost-of-being-wrong (irreversible data shapes,
public APIs, multi-week slices), run a second premortem on the plan itself before
showing it to the user — Phase 0.5 stress-tested the idea, this one stress-tests the
implementation strategy.

### Phase 4: Implementation (Ralph Loops)
For each step: identify the riskiest sub-task and attack it first, implement with literate
style, write comprehensive tests, validate, fix, repeat. The loop converges because each
iteration gets verbatim error feedback and because it ratchets — `ratchet.py` refuses an
iteration where an obligation that passed before has quietly stopped passing, and naming
which one is what lets the next attempt aim. Repair is the default; resampling N candidates
and keeping whichever survives the checks is the alternative where checks are cheap and
candidates small, and the acceptance criterion is the same either way. Each step runs on an execution-tier model with a
2-iteration budget; on non-convergence it returns a structured failure report (failing tests
verbatim, hypotheses ruled out, suspected root cause, suspected spec gaps) and a judgment-tier
agent continues from that report — up to 7 iterations total, then the step gets split.

### Phase 5: Quality Audits
Multi-axis: test gaps, security, performance, UX, spec compliance, simplicity, provability.
Audits fan out on the execution tier (a deterministic Workflow pipeline where the harness
provides one, parallel subagents otherwise); each critical/high finding is then adversarially
verified by a judgment-tier skeptic before any fix is attempted. Ralph Loop the audits
themselves — audit -> fix -> re-audit until 0 criticals.

### Phase 6: KB Sync
After implementation, verify the KB still matches reality. Update stale files. The KB is
the source of truth — if code contradicts spec, flag it.

### Phase 7: Documentation & Validation
Write user-facing documentation, integrate user-facing instructions as tests so the doc
stays valid, run final validation, and present results.

## Core Principles

1. **Spec before code** — you can't validate what you haven't specified
2. **Premortem before you build** — challenge the idea (Phase 0.5) and the plan (Phase 3)
   by assuming they already failed; blind spots are cheaper to find here than in code
3. **Tackle uncertainty and blockers first** — within any plan, step, or coding session,
   the hardest and most uncertain work goes first. Deferring risk feels productive but is
   how projects discover at the last minute that a core assumption was wrong
4. **Fix the harness, not the output** — when the agent fails, improve the constraints
5. **Enforce, don't request** — a lesson, property, guideline, or convention that matters
   gets a deterministic check, written at the moment the rule is: a test, a linter rule, a
   CI script, a hook. Build the tool on the fly; it is usually smaller than the discussion
   about whether to build it. A rule with no check is a rule you are hoping about, and the
   hoping is invisible — which is why the declaration is mandatory and "nothing checks this,
   because <reason>" is the only honest alternative
6. **Invest in the KB** — specifications, properties, and SDK research pay off across every implementation step
7. **External deps are dangerous** — always research actual runtime behavior (lazy-loading,
   rate limits, request costs) before building on an SDK
8. **Ralph Loops converge if they ratchet** — the feedback loop is the mechanism, and
   keeping what passed is what turns iteration into progress; hope is not a strategy
9. **Prefer unrepresentable to caught** — a type or capability that makes the wrong
   answer impossible beats a test that catches it, and a proof beats both for a
   critical core, provided what the proof does not cover is written beside it
10. **Agent navigation != human navigation** — routing tables, not prose
11. **Route models by difficulty** — judgment-tier tokens buy specs, plans, and verification,
    not typing; execution tiers escalate with a failure report when they stop converging. An
    execution agent stuck on a fully-specified task is usually reporting a spec defect
12. **Engineer the engineer too** — maintain a map of the user's demonstrated understanding
    and calibrate every question, brief, and plan to it; alignment between the user's mental
    model and the KB is a correctness condition, not a courtesy
