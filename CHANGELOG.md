# Changelog

## 0.8.0 — 2026-10-13

- Agents now learn about new kit releases. `tools/update-check.py` runs from a
  session-start hook and compares the installed release tag with the newest tag
  on the kit's `origin`. It checks the network at most once a day.
- When a newer release exists, the agent proposes the update once per session.
  It summarizes the changelog entries in between, and updates only with consent.
  The update is a fast-forward to the release tag, then `sync-skills.sh --check`.
- The script stays silent when the kit is current, offline or untagged. It always
  exits 0, so a failed check never blocks a session.

Compatibility: opt in per user. Merge `templates/settings/kit-update.settings.json`
into `~/.claude/settings.json`. The notice reaches new sessions only.

## 0.7.0 — 2026-10-13

- The design stays proof-ready without a proof assistant. At any time, someone can
  start a Rocq or Lean proof of the underlying model, and the code maps onto it.
- Each stateful subsystem gets a model in `kb/models/`: state, operations,
  invariants `I<n>`, a refinement map and proof notes. The new template is
  `templates/kb/models/_TEMPLATE-MODEL.md`.
- Every plan step carries a `Proof:` sketch. An execution step cites an existing
  model invariant and gives an `Argument:` and a `Refinement:`. A step with no
  behavior change writes `Proof: none: <reason>`. `plan-check.py` checks this shape.
- Design rules keep code close to the model: a pure core, explicit state, total
  functions and one entry point per operation. Breaking the refinement map needs an ADR.
- Each cited invariant gets a property-based test named by its ID. An agent stops
  and fixes the sketch when the code needs an argument the sketch does not give.
- A sketch is not a proof. The script checks that the sketch exists and cites a real
  invariant. It does not check the argument.

Compatibility: existing plans fail `plan-check.py` until every step has a `Proof:`
field. Projects without models start with `Proof: none: <reason>` on each step,
then add models one subsystem at a time.

## 0.6.0 — 2026-10-13

- Human-facing artifacts now follow a writing standard: the rules of ASD-STE100,
  Simplified Technical English. The project glossary replaces the STE dictionary.
  The standard is in `docs/writing-standard.md`.
- New `ste-check.py`: it fails a sentence over 25 words, or over 20 in a numbered
  procedure. It also fails a word that the glossary rejects with `Not:`.
  It warns on *should*, *may*, *might* and on the passive voice.
- The plan exit gate runs `ste-check.py` on `kb/plan.md`. Forebrief card text and
  the kit's newest changelog entry follow the same standard.
- The checks are structural. The kit uses no readability score. The script does
  not check that a sentence says one thing or that the reader can act on it.

Compatibility: projects copy `ste-check.py` into `tools/`. Existing plans can fail
on long sentences until someone shortens them. Glossary entries without `Not:`
behave as before.

## 0.5.0 — 2026-10-09

- Phase 3 plans now mark each step's tier: `execution` or `judgment`. An execution step
  settles every choice in the plan: files, interfaces, one checking command per
  acceptance criterion, what is out of scope, and when to hand off. The format is in
  `skills/spec-driven-dev/references/execution-ready-steps.md`.
- New `plan-check.py` gate: it refuses a step with no tier or no checking command. It
  also refuses an execution step with a missing field, or with open-choice wording
  ("choose", "TBD", "as needed", ...) outside its scope, hand-off and unknown fields.
- For execution steps, the plan-simulation subagent now runs on the execution model.
  Any question it raises means the step is not ready. Execution agents end an attempt
  rather than settle an open choice.
- `plan-check.py` checks the shape of a step only. It does not show that the choices are
  right or that a command tests its criterion. It also does not show that the execution
  model can handle the task class: the capable-reference rule still applies.

Compatibility: projects adopting the gate vendor `plan-check.py` into `tools/` and add
`Tier:` and the execution fields to `kb/plan.md`. Existing plans fail the gate until
every step declares a tier.

## 0.4.1 — 2026-10-08

- Add `sync-skills.sh --expected-revision <full-commit-sha>` to refuse a different
  source HEAD or Git-visible changes anywhere in the kit before changing host links.
  Empty pins are refused. Shared instructions and tools are covered alongside skills.
- Preserve link-only checking when the option is omitted. The revision check is
  point-in-time: Git-ignored files and concurrent mutations are outside its guarantee;
  it does not prove release publication or what an active agent has loaded.
- Clarify forebrief cards: each option states its effect on the plan and who acts.
  Document human review evidence and forbid agent-authored UI confirmations.

Compatibility: existing installation commands are unchanged. Projects with a declared
kit revision opt in with `--check --expected-revision <full-commit-sha>` and keep
publication, installation and executed agent adoption as separate evidence.

## 0.4.0 — 2026-10-06

- Phase 1 asks more of the right questions: an assumption ledger (`kb/assumptions.md`)
  records every unsettled choice, an independent subagent writes its own questions each
  round, an overridden default forces another round, and `assumption-check.py --exit`
  replaces "the user confirms" as the exit gate. Slices check the ledger before planning.
  The ledger's completeness remains unchecked: a choice nobody noticed has no row.
- Renamed to Socrask: the public repository is `yurug/socrask` (formerly
  `yurug/agentic-loop-kit`; GitHub redirects the old URL). Update clones with
  `git remote set-url origin https://github.com/yurug/socrask.git`.
- Primitives: choose the perception before the renderer. New rail, lanes and layers
  entries, a visual-language reference and composition specs; diagrams are reserved
  for topology. Package paths move from `@backbrief/primitives` to `@brief/primitives`.

Compatibility: projects already past Phase 1 are unaffected. Projects adopting the exit
gate vendor `assumption-check.py` into `tools/` and create `kb/assumptions.md` from
`templates/kb/assumptions.md`; run it without `--exit` in CI, with `--exit` at Phase 1 exit.
Primitives consumers update imports to `@brief/primitives`.

## 0.3.1 — 2026-10-05

- Preserve prior feedback IDs and event records against a fixed Git rollout commit
  and intervening branch/merge ledger states; deletion cannot hide behind a later commit.
- Reject symlink paths that would compare a different ledger’s history.
- Ignore replacement objects; refuse incomplete or grafted history and report the exact comparison scope.
- Keep snapshot-only imports explicit; adopting projects must wire the history base
  and prove a removed-event refusal through their real CI launcher.

Compatibility: ledger version 1 is unchanged. History checking is enabled by
`--history-base`; without it, the receipt explicitly reports that history was not checked.


## 0.3.0 — 2026-10-04

- Add a versioned project/plan/task/feedback ledger and read-only consistency gate.
- Check captured-request coverage, ownership, next review/action, dependencies and WIP.
- Refuse product closure without matching implementation, delivery and case evidence;
  repeated failed feedback invalidates older acceptance and reopens the same task.
- Expose unverified imported history instead of treating legacy status as acceptance.
- Route the method through the skill, project template, CI self-tests and adoption guide.
- Isolate Git hook environment so repository fixtures run under the same local CI gate.

Compatibility: existing projects opt in by declaring their feedback sources and wiring
`tools/project-check.py` into their actual CI/handoff entrypoint. Historical claims can be
imported explicitly as unverified. A coherent ledger does not prove product acceptance;
source capture, evidence authenticity and semantic review remain the team's responsibility.

## 0.2.0 — 2026-10-02

- Add a read-only user-outcome gate: complete required scenarios, exact contract digest,
  immutable candidate identity observed before/after, freshness and fixture/checker lineage.
- Preserve first-attempt success and recovery separately; compare repeated outcomes with
  a baseline and report total duration/cost without turning an eventual success into a
  clean first attempt. Missing, skipped and unknown cases fail validation.
- Connect feedback to representative state, acceptance evidence and delivery ownership.
  Keep comprehension, implementation, deployment and product acceptance distinct.
- Replace unconditional cheap-model-first routing with demonstrated task quality;
  record auxiliary models and measure total cost per useful result. Scope audits by risk.
- Install/check selected skills for Claude and Codex, preserving unrelated files and
  requiring explicit symlink replacement. Document mailbox ACK plus executed adoption.

Compatibility: the obligation ratchet and existing suites are unchanged. Projects adopt
the outcome gate through an explicit report adapter and promotion command; installation
alone does not wire project CI or establish product success. Reports are declarations,
not authenticated attestations. No live product or model default is changed by this release.

## 0.1.0 — 2026-09-25

First tagged release: concurrent local worktrees with explicit ownership and
human checkpoints.

- Add atomic path claims, shared-resource leases, commit-bound technical handoffs,
  coordinated integration, and explicit interrupted-command recovery.
- Connect Inbrief start disposition and Backbrief final-diff evidence to coordinator
  lifecycle gates; workers use one coordinator for human communication.
- Clarify Laconic as concise, decision-focused communication; persistent personal
  models are opt-in, and questions never automatically demote understanding.
- Replace raw-log ratchet extraction with versioned complete test results, unique
  test IDs, atomic writes and serialized state transitions.
- Add safe personal-repository enrollment, linked-worktree support, staged-path
  guard and preservation of tracked/foreign artifacts.
- Run resolver, alignment, enrollment and concurrent-process regression tests in
  the shared local/CI gate.

Compatibility: raw `ratchet.py --from-log` and implicit stdin are rejected. Migrate
using `docs/ratchet.md`. Collaboration requires POSIX Python 3 and local filesystem
locking. Independent clones/hosts are not coordinated. Human evidence references
are checked for consistency, not authenticated; no claim of automatic comprehension.
