# Verify agent adoption

Which features a project adopts, and how it vendors kit files, is in
[adoption levels](adoption-levels.md). This page covers agents loading the installed kit.

A published kit is not necessarily the kit an active agent loaded. Use the team's
existing mailbox, with explicit authorization to message its participants. Preserve
its append-only protocol and real sender identities; never write another agent's ACK.

1. Announce scope and paths before editing shared instructions. Give the published
   repository, exact commit/tag, changed rules, installation/check commands and
   requested project action. Preserve concurrent work and shared test-resource locks.
2. Install the same reviewed skill for each intended host. For example:

   ```sh
   ./sync-skills.sh --target both --only spec-driven-dev
   ./sync-skills.sh --target both --only spec-driven-dev --check
   ```

   Claude links live under `~/.claude/skills`; Codex links under `~/.codex/skills`.
   Real files/directories are preserved and cause failure. Foreign symlinks require
   deliberate `--replace-links`; preflight refuses known conflicts before changes.
   Host directory overrides support isolated tests. Avoid concurrent installers;
   this is a local convenience tool, not a transactional or hostile-user boundary.
   Other skills and host settings are untouched when `--only` is used.

   For a project that declares an exact kit commit, bind the check to that commit:

   ```sh
   ./sync-skills.sh --target both --only spec-driven-dev --check --expected-revision <full-commit-sha>
   ```

   This refuses a different source HEAD or tracked/untracked changes anywhere in the kit
   before installing any links, including shared instructions and tools. Git-ignored files are excluded; unrelated kit edits must also be committed before this check. Without this option,
   `--check` validates link destinations only: a link to a moving checkout does not pin
   a version. This is a point-in-time check, not an immutable installation; rerun it at
   adoption and release gates. Concurrent changes are not prevented by an atomic snapshot.
   It does not establish publication or active-agent loading.

3. Ask each active agent to re-read the installed skill and outcome/adoption references
   now; an active conversation may retain old instructions despite updated files.
   Project instructions take precedence, so reconcile conflicting local rules in a
   scoped change. Keep instructions in one routed location instead of copying the
   entire kit into several host files.
4. Require a reply identifying the kit SHA, resolved skill path, command actually run,
   exit status/evidence and the first project application. A receipt saying only
   "received" means acknowledged, not adopted. A fixture/self-test means the tool works,
   not that the product journey passed. Ask for both a positive and a negative gate
   example before trusting a new report adapter.
5. The integration owner verifies that the real delivery entrypoint calls the gate
   and retains a complete baseline/candidate pair. Track unresolved feedback and
   first-attempt outcomes on the exact delivered version. Confirm state/bytes/UI for
   the affected journey; a test count or new methodology document is not that proof.

For project-control adoption, also reconcile the declared feedback/backlog inventory
into the project's work ledger. Execute its checker and an omission/false-closure
negative through the actual CI launcher. For Git-backed work, pin the reviewed rollout
commit and verify `history.checked: true`; retain a removed-failure negative through
the same launcher, including a missing-pin refusal. Record remaining imported uncertainty,
owners and review dates; a coherent registry does not close its product outcomes.

Keep a small adoption receipt in the project's established evidence location:
agent, kit SHA, resolved path, ACK reference, executed command/result, application
artifact and remaining gaps. Mark missing replies pending; silence and elapsed time
never authorize changes or demonstrate adoption. Follow up through the existing channel.

For the first quality iteration, limit work in progress to a few complete journeys.
Compare failures, recovery, time to usable result and cost per successful task. Model
experiments record every effective helper plus prompts, tools, context and budgets;
validate cheaper routing against a capable reference before optimizing costs. Preserve
processing/privacy constraints and use synthetic data when a supplier is unqualified.

Enforcement: `sync-skills.sh --check` checks links, `tools/test-skill-sync.py` checks real
installation/refusal, and `tools/outcome-check.py` checks supplied outcome evidence.
Authenticity of mailbox replies, whether an agent read instructions, quality of human
judgment, and actual project gate integration still require inspection; no script here
claims to guarantee those facts.

## Stay current

Merge `templates/settings/kit-update.settings.json` into `~/.claude/settings.json`.
At session start, `tools/update-check.py` compares the installed release tag with
the newest tag on the kit's `origin`. It checks the network at most once a day.
When a newer release exists, the agent gets a notice and proposes the update once.
The agent reads the changelog entries in between before it asks. It updates only
with consent: `git pull --ff-only` to the release tag, then `sync-skills.sh --check`.
A project that pins a kit commit updates its pin in a separate commit.

The notice reaches new sessions only. A running session learns of a release at its
next start.
