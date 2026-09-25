# Repository layout and mechanics

Technical reference for people working *on* the kit. If you only want to use it, the README
and `GETTING-STARTED.md` are enough.

## Tree

```
skills/                Claude Code skills, one directory per skill (<name>/SKILL.md)
  spec-driven-dev/     The main skill, plus:
                         kb-lint.py                  mechanical KB validation
                         ratchet.py                  what passed stays passed
                         kb-lint-forebrief.py        verbatim-rationale check
                         fixtures/kb-lint/           fixtures for the enforcement channels
                         fixtures/forebrief-lint/    fixtures for the verbatim rule
                         test-kb-lint.sh             runs the kb-lint fixture suite
                         test-ratchet.sh             runs the ratchet suite
                         test-kb-lint-forebrief.sh   runs the forebrief fixture suite
  forebrief/           Skill and public wire references for forebrief decision sessions
sync-skills.sh         Symlinks every skill into ~/.claude/skills/ (idempotent)
tools/skill-check.py   Validates public skill metadata and shipped references
GETTING-STARTED.md     Bootstrap prompts and the KB-usage enforcement stack
templates/
  kb/                  Knowledge base directory template (agent-optimised structure)
  claude-md/           CLAUDE.md templates, routing protocol at the top
  settings/            SessionStart hooks: kb/INDEX.md injection, forebrief status
  forebrief/           Fold-in templates (round digest, ADR) that forebrief vendors
methodology/           The methodology, phase by phase
docs/                  Repository mechanics and the one-line-per-check harness inventory
```

## Skill discovery

Claude Code discovers skills in directory form only, at
`~/.claude/skills/<name>/SKILL.md`. Flat `.md` files in that directory are ignored, which is
why `sync-skills.sh` symlinks directories rather than files.

## Why the knowledge base actually gets used

Instructions asking an agent to read the knowledge base are not load-bearing. Two mechanisms
are:

- **Injection**: the `SessionStart` hook in `templates/settings/` puts `kb/INDEX.md` into
  context before the first turn, so the routing table is present whether or not the agent
  thinks to look for it.
- **Lint**: `kb-lint.py` fails the build when the knowledge base drifts out of the shape the
  skills expect, so drift surfaces as a red check rather than as a silently ignored file.

`GETTING-STARTED.md` documents the full enforcement stack and the prompts that install it.

## The lint suite

```bash
tools/ci-local.sh                    # everything below, one exit code
./skills/spec-driven-dev/test-ratchet.sh
tools/harness-inventory.sh           # every checker is listed in docs/harness.md
python3 skills/spec-driven-dev/kb-lint.py <path-to-kb>
./skills/spec-driven-dev/test-kb-lint.sh
./skills/spec-driven-dev/test-kb-lint-forebrief.sh
```

`tools/ci-local.sh` is the kit applying its own rule to itself: install it with
`ln -sf ../../tools/ci-local.sh .git/hooks/pre-commit` and the suites stop depending on
anyone remembering them. Git hooks are not versioned, so that step is per-clone.

`test-kb-lint.sh` runs `kb-lint.py` against `fixtures/kb-lint/`, one fixture per
enforcement-channel defect: a property with no `Enforced-by:` line, an `instruction:`
channel (rejected on purpose — prose is not enforcement), a channel naming a file nobody
wrote, and a `none:` used as a rubber stamp. Each `fail-*` fixture must fail with *its own*
error code, so an unrelated broken link cannot mask a regression.

`test-kb-lint-forebrief.sh` runs `kb-lint-forebrief.py` against
`fixtures/forebrief-lint/`, which cover the verbatim-rationale rule: a folded decision must
carry the human's own words, not an agent's paraphrase of them.

## Collaboration and release validation

- [Concurrent agents](concurrent-agents.md): atomic claims, resources, integration and recovery.
- [Human checkpoints](alignment.md): coordinator-owned Inbrief and final Backbrief.
- [Shared repositories](shared-repositories.md): safe personal enrollment and guard limits.
- [Ratchet results](ratchet.md): complete structured results and migration from raw logs.

The local gate includes real concurrent-process/worktree tests and checkpoint/enrollment fixtures.
