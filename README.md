# Agentic Loop Kit

[![CI](https://github.com/yurug/agentic-loop-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/yurug/agentic-loop-kit/actions/workflows/ci.yml)

The loop I run when I build software with coding agents, packaged so you can run it too.

Agents write code faster than any of us can absorb it. My problem was never the code they
produced; it was that after a few autonomous cycles I could no longer explain the system I
was supposed to be accountable for. This kit is the answer I converged on: onboard the
engineer, resolve the ambiguity, write the spec and the knowledge base, let the agent produce
a change, run the checks, and re-align the engineer at the end of every cycle.

It runs today on Claude Code, as a set of skills plus the templates they expect.

## Try it

Install the skills once per machine:

```bash
./sync-skills.sh
```

Each `skills/<name>/` directory is symlinked into `~/.claude/skills/`, so this repository
stays the single source of truth: edit a skill here and it is live immediately.

Then, from any project:

```
/spec-driven-dev
```

Starting from zero? `GETTING-STARTED.md` carries the exact bootstrap prompt, the prompt for
adopting the methodology on an existing codebase, and what to run day to day.

For the full reference loop, also install
[engineer-engineering-tools](https://github.com/yurug/engineer-engineering-tools):

```bash
git clone https://github.com/yurug/engineer-engineering-tools.git
cd engineer-engineering-tools && ./install.sh
```

That supplies `inbrief` for grounded onboarding, `forebrief` for human-owned decisions, and
`backbrief` for the comprehension checkpoint after every non-trivial change. The Markdown
fallbacks keep bootstrap possible, but they are degraded modes: they cannot enforce the
human credential boundary, preserve a decision session as an append-only log, or maintain a
cited comprehension map across cycles.

## What you get

- A written specification and a knowledge base your agent reads before it writes anything,
  instead of a chat scroll nobody can query.
- Ambiguity resolved on purpose, up front, in a round of questions and recorded answers,
  rather than discovered as wrong code three cycles later.
- A harness that decides what ships, and a routing rule for failures: fix the agent, the
  spec, or the checks, never the symptom.
- A per-cycle alignment checkpoint, so the human who signs off can still explain what
  changed.
- Premortems before you build, so the idea and then the plan get stress-tested while
  changing your mind is still cheap.

## Where it fits

This kit implements the loop argued for in
[Why a loop at all](https://yann.regis-gianas.org/en/posts/harness-not-output/),
whose phases lean on four disciplines:

1. **Software engineering**, because the agent reads your code as input; structure now pays
   twice.
2. **Knowledge engineering**: specifications, properties, invariants, and acceptance
   criteria, written for exactly one reader, the agent.
3. **Harness engineering**: the checking machinery that makes a stochastic process converge,
   from deterministic checks to auditors to Ralph loops.
4. **Engineer engineering**: keeping the accountable human's mental model aligned with the
   system, which is a correctness condition and not a courtesy.

The reference stack uses
[engineer-engineering-tools](https://github.com/yurug/engineer-engineering-tools) for
`inbrief`, `forebrief`, and `backbrief`: before, during, and after the work. `laconic` is the
reference implementation of the persistent engineer model and calibrated communication
shared by all three; it is not publicly distributed yet, so the kit ships a compatible,
auditable Markdown fallback rather than dropping the alignment invariant. Finally,
[rocqeteer](https://github.com/yurug/rocqeteer) gives the harness its strongest check,
formal verification of critical modules.

## What is inside

| Path | What it holds |
|---|---|
| `skills/` | The Claude Code skills, one directory per skill |
| `templates/` | Knowledge base, `CLAUDE.md`, and session-hook templates |
| `methodology/` | The methodology written out, phase by phase |
| `docs/` | Repository layout, enforcement stack, and other technical notes |

## Status

Pre-1.0 release candidate. The methodology is still evolving, but every deterministic
check shipped by the kit runs through `tools/ci-local.sh` and the same gate runs on every
push and pull request. The supported installation target for this release is Claude Code;
the full workflow expects `inbrief`, `forebrief`, `backbrief`, and an engineer model.
Explicit fallbacks exist for bootstrap and constrained environments, but are not presented
as equivalent to the reference tools.

If you run it, tell me what broke. Issues, pull requests, and a plain "this made no sense
to me" are all welcome.

## License

MIT
