# Getting started

How to start a project with the methodology — and, more importantly, how to make sure
the knowledge base keeps getting used and maintained after the first session ends.

## Why the prompt below looks paranoid

Nothing guarantees an agent uses a KB. There are only three channels, of decreasing
reliability:

1. **Presence** — content injected into every session (CLAUDE.md, SessionStart hooks).
   Guaranteed to be seen.
2. **Instruction-following** — "read `kb/INDEX.md` first" written somewhere the agent
   reads. Probabilistic: compliance is high on big confusing tasks and decays on tasks
   that look trivial — exactly the tasks where properties get silently violated.
3. **Collision** — assertive filenames surfacing in the agent's own grep. Useful, but
   retrieval by accident, not routing.

Maintenance is even weaker: an agent that changes behavior has no natural reason to
update a markdown file about it. So the kit enforces usage and maintenance with four
mechanisms, installed by the skill's **Step 2d** and named explicitly in the bootstrap
prompt in case the skill drifts or isn't installed:

| Mechanism | Channel | What it buys |
|---|---|---|
| `CLAUDE.md` routing protocol (top of file) | presence → instruction | every session is told, per task: load the bundle, same-commit KB updates |
| SessionStart hook injecting `kb/INDEX.md` | presence | the routing table is in context before the first token — compliance not required |
| `tools/kb-lint.py` in pre-commit + CI | mechanical | the only hard guarantee: broken links, missing frontmatter, oversized files, missing indexes, stale `last-updated`, properties with no enforcement channel fail the build |
| `tools/ratchet.py` in CI | mechanical | what passed stays passed: a run where a previously-passing obligation vanished fails, and names it; retiring one needs a stated reason |

Those four rows are one instance of a general rule, not a KB-specific trick. **Anything
you want held picks one of these channels, and only the mechanical rows survive a session that is in
a hurry.** So pick the channel when you write the rule, and build the checker if one is
possible — a `grep` in CI, a hook that reads the diff, a counter with a threshold. That is
thirty lines, and it is the difference between a convention and a guarantee. This kit does
it to itself: `skills/primitives/visual-check.py` fails on an unmarked hand-rolled visual,
`tools/primitives-adoption.sh` counts adoption against a number that says stop, and
`kb-lint` refuses a property that names nothing to enforce it. Where a rule genuinely
cannot be checked, write the reason beside it — an audit can weigh a stated reason and
cannot weigh a silence.

## Prerequisites (once per machine)

```bash
git clone https://github.com/yurug/agentic-loop-kit.git
cd agentic-loop-kit && ./sync-skills.sh
```

For the full workflow, install the public engineer-engineering tools too:

```bash
git clone https://github.com/yurug/engineer-engineering-tools.git
cd engineer-engineering-tools && ./install.sh
command -v inbrief forebrief backbrief
```

`inbrief`, `forebrief`, and `backbrief` are the reference mechanisms before, during, and
after the work: grounded onboarding, human-owned decisions, and the per-cycle comprehension
checkpoint. The skill can bootstrap with Markdown when they are absent, but it must identify
that path as degraded. The engineer model itself is never optional: use `laconic` when
installed, otherwise use the compatible plain-file fallback bundled in the `spec-driven-dev`
skill until laconic is publicly distributed.

## Starting a new project — the prompt

Open Claude Code in the (empty) project directory and paste, filling in the idea:

```
/spec-driven-dev <one-paragraph description of what to build, for whom,
and what success looks like>

Non-negotiable, before Phase 3: install the KB usage harness exactly as
Step 2d of the skill specifies —
1. CLAUDE.md from the kit's templates/claude-md/spec-driven.md, with the
   "KB routing protocol" section at the top;
2. the SessionStart hook from templates/settings/kb-sessionstart.settings.json
   merged into .claude/settings.json, so kb/INDEX.md is injected into every
   future session;
3. kb-lint.py and ratchet.py copied from the skill directory into tools/ and
   wired into pre-commit and CI, errors failing the build;
4. a one-line-per-check harness inventory with a fixed line budget.
Then prove it: kb-lint exits 0, and a fresh subagent given only this
directory names the KB routing protocol without being told where to look.
The methodology fails silently without this step — future sessions would
grep the code and never open the KB.
```

The first paragraph is the input to Phase 0.5–1 (premortem, onboarding brief, then
ambiguity rounds).
The second paragraph is deliberately redundant with the skill: harness installation is
the one step whose omission is invisible until weeks later, so it is the one step the
prompt re-states. If everything works you paid a few redundant lines; if the skill
regressed or a different model cuts corners, the prompt still forces the harness.

## Adopting the methodology on an existing project

```
Read `/path/to/agentic-loop-kit/methodology/spec-driven-development.md` and
`/path/to/agentic-loop-kit/skills/spec-driven-dev/SKILL.md`, then retrofit this project:
1. Build the KB (Phase 2 structure) from the existing code and docs —
   ambiguities you cannot resolve from the code become questions for me
   in kb/questions-round1.md.
2. Install the usage harness (Step 2d): CLAUDE.md routing protocol,
   SessionStart hook, kb-lint in pre-commit/CI.
3. Run kb-lint and the KB quiz; fix errors and gaps.
Do not modify any product code in this session.
```

For a pre-2026 KB that lacks `type`/`summary` frontmatter, lint with
`--required-keys id,domain,last-updated` until the files are migrated.

A KB whose properties predate the enforcement rule fails on every entry at once, and there
is deliberately no flag to turn that off — the point of the check is that the gap is
visible. The migration is mostly mechanical: most such files already carry an informal
"Test strategy" line, which becomes `Enforced-by: test:<path>::<id>` where that test exists
and `none: <reason>` where it does not. Do the honest pass first, then read the `none:`
count. That number is the size of the gap between what the project claims and what it
checks, and it was there before the linter could see it.

## Day-to-day sessions

No special prompt — that is the point. The hook injects `kb/INDEX.md`, CLAUDE.md
carries the per-task protocol, and lint guards the commits. If you observe an agent
ignoring the KB anyway, treat it as a harness bug, not an agent mood: tighten the
routing protocol wording, check the hook fires (`claude --debug`), or add the missing
bundle to `kb/indexes/by-task.md`. Fix the harness, not the output.

## Verifying the harness (any time)

```bash
python3 tools/kb-lint.py kb          # 0 errors expected once you have filled the template in;
                              # a fresh copy fails on the YYYY-MM-DD and <type>
                              # placeholders, which is the point of them
python3 tools/kb-lint.py kb --strict # gate releases: warnings fail too
```

And the end-to-end probe — start a fresh session and ask:

```
Without using any tools: what does this project's KB routing protocol
require before any task?
```

A correct answer proves the presence tier works: the session knew before it could grep.
