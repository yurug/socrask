# Changelog

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
