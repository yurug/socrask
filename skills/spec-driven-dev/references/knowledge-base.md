# Knowledge-base construction

Read this reference in full before executing Phase 2.

## Contents

- [Phase 2: Knowledge Base Creation](#phase-2-knowledge-base-creation)
- [Create the directory structure](#step-2a-create-the-directory-structure)
- [Create files in order](#step-2b-create-files-in-this-order)
- [Audit the KB](#step-2c-kb-audit-ralph-loop-max-10-iterations)
- [Install the usage harness](#step-2d-install-the-usage-harness-not-optional)

## Phase 2: Knowledge Base Creation

The KB is designed and optimized for **agent navigation** — precise context, few tokens, few hops.
A subagent retrieves a few chunks at a time, ranks files by title and frontmatter before opening
them, and pays a context cost for every hop. Design the KB to fit that consumer.

**Core principles** (each one is concretely actionable, not a slogan):

- **Atomic** — one concept per file. If a fact needs another file's body to make sense, split or inline it.
- **Assertive titles** — the filename is a complete claim that answers "what is in this file?"
  (e.g. `auth-token-ttl-15min.md`, not `auth.md`). Agents rank on titles before opening.
- **Stable paths** — once committed, a file's path does not change. Rewrite contents in place;
  broken links silently corrupt retrieval and the agent has no way to detect dangling refs.
- **Frontmatter triages** — every file declares `summary` (one sentence), `type` from a closed
  set (`concept | decision | constraint | procedure | spec | external | index | glossary`), and
  `tags` drawn from the controlled vocabulary in `kb/GLOSSARY.md`.
- **Typed links over bare refs** — relations carry meaning (`depends-on`, `refines`, `contradicts`,
  `supersedes`, `broader`, `narrower`). The agent prunes the graph without opening targets.
- **Glossed links** — every cross-reference includes a one-line gloss of why the target matters
  here. Saves the agent a retrieval hop.
- **One register per type** — a file answers in the mode its `type` declares: `procedure`
  files are steps that link to the ADR for rationale; `decision` files carry rationale and
  do not restate steps; `spec` files are pure reference. Blending "why" into a "how-to" is
  structural noise the agent pays for on every load.
- **Define once** — terms are defined in `kb/GLOSSARY.md` and nowhere else; content files use
  them bare, linking on first load-bearing use. A re-definition costs tokens in every hop
  that loads the file and drifts from the canonical one.
- **Indexes are routing tables, not summaries** — small (<25 links each), curated, with a one-line
  gloss per entry. Folders are invisible to retrieval; indexes are the navigation layer.
- **Header-aligned content** — H2/H3 sections bound one self-contained idea so chunkers split on
  semantic boundaries, not mid-argument.
- **Each file < 200 lines** — split when longer. Sinks (raw source data) are linked from the graph
  but only loaded when the agent needs to dive in.

### Step 2a: Create the directory structure

```bash
mkdir -p kb/indexes kb/domain kb/spec kb/properties \
         kb/architecture/decisions kb/external \
         kb/conventions kb/runbooks kb/reports
```

### Step 2b: Create files in this order

1. **`kb/GLOSSARY.md`** — every domain term, canonical names
2. **`kb/domain/prd.md`** — Product Requirements Document:
   - User stories, commands with examples, non-functional expectations, out of scope
3. **`kb/spec/`** — split into focused files:
   - `data-model.md` — entities, fields, types, constraints, defaults
   - `algorithms.md` — step-by-step with state machines or pseudocode
   - `api-contracts.md` — inputs, outputs, error codes per interface
   - `config-and-formats.md` — config schema, file formats with examples
   - `error-taxonomy.md` — every error type, when it occurs, user message
   - `INDEX.md` — routing table for spec files
4. **`kb/properties/`** — split into:
   - `functional.md` — P1, P2, ... invariants (ID, name, statement, violation example, WHY)
   - `non-functional.md` — NF1, NF2, ... measurable criteria
   - `edge-cases.md` — T1, T2, ... boundary conditions with expected behavior
   - `INDEX.md`

   **Every entry declares what enforces it.** Each `P<n>`/`NF<n>`/`T<n>` carries an
   `Enforced-by:` line naming what fails when it breaks. The vocabulary is ordered
   strongest-first, and the order is the recommendation:
   `structural:<path>` (a type, capability, or construction that makes the violation
   unrepresentable) → `proof:<path>` (machine-checked, universal over the property as
   stated) → `test:<path>::<name>` → `mechanical:<path>[#<code>]` → `hook:<path>` →
   `none: <reason>`.

   **Prefer a wrong answer that cannot be represented to one that is merely caught.**
   Before writing a test for a property, spend one minute asking whether the type
   system, an opaque constructor, or a capability could make the violation
   impossible to express — a structural channel needs no maintenance, cannot be
   skipped, and does not rot. A `proof:` channel must also say what the proof does
   NOT cover — the statement, the boundary, the kernel — on a `Trusted:` or
   `Not covered:` line; `kb-lint` warns (`W-trust`) when it does not, because a
   proof with an unnamed boundary reads as a guarantee over the whole system, which
   is the one thing it is not.
   The vocabulary is closed and `instruction:` is not in it: prose raises a probability, it
   does not hold an invariant, and a channel that admitted prose would let every property
   pass by pointing at a paragraph. `kb-lint` fails the build on a missing channel
   (`E-unenforced`), an unknown one or one naming a file that does not exist (`E-channel`),
   or a `none:` with no real reason (`E-noreason`). Start from
   `templates/kb/properties/functional.md`, which carries the vocabulary and a worked entry.
   Reach for `none:` last — most unchecked properties are properties whose thirty-line
   checker nobody has written yet.
5. **`kb/architecture/overview.md`** — module structure, DI pattern, dependency graph, error hierarchy
6. **`kb/architecture/decisions/`** — at least 2 ADRs for significant design choices
   - Format: Context, Decision, Consequences, What this means for implementers,
     What this does not cover (adjacent decisions not made here; what breaks if the context changes)
7. **`kb/external/`** — MANDATORY: one file per third-party SDK/API
   - Document ACTUAL RUNTIME BEHAVIOR: lazy-loading, pagination, rate limits, batching
   - Compute REQUEST BUDGET: for realistic workload, how many API calls?
   - If budget > 100 calls for a basic operation, mandate bulk-fetch-then-join in architecture
   - **A load-bearing dependency a research report recommends gets DECIDED before it is
     used, not adopted by reading.** A report surveys alternatives and gives reasons —
     that is deliberation, not a decision, and afterwards an accepted recommendation and
     an unexamined default are indistinguishable. Put the choice to the user (a forebrief
     card, or an explicit question) naming the real alternatives, before code depends on
     it. Learned the hard way: a rendering engine entered a library through a research
     synthesis and became load-bearing while the only questions ever asked were which
     package of that engine to bundle and which of its modes to use — both presupposing
     the choice nobody made.
8. **`kb/conventions/`** — code-style.md, error-handling.md, testing-strategy.md
9. **`kb/runbooks/audit-checklist.md`** — structured quality checklist
10. **`kb/indexes/by-task.md`** — for each task type (implement, audit, debug, test): ordered file list + "key questions this answers"
11. **`kb/INDEX.md`** — LAST (needs to reference everything):
    - 2-sentence project summary
    - "How to use this KB" with reading order
    - Quick-load bundles table: goal -> ordered file list
    - File count

This is a starting structure — let it evolve as the project grows. Skip categories that don't apply
yet (match KB depth to current scope), and reorganize when an agent struggles to navigate.

### Every content file MUST have:

```markdown
---
id: <stable-unique-id>           # never changes once committed
type: <concept|decision|constraint|procedure|spec|external|index|glossary>
summary: <one sentence — the claim or fact this file establishes>
domain: <topic>
tags: [<tag>...]                 # from the controlled vocabulary in kb/GLOSSARY.md
last-updated: <YYYY-MM-DD>
depends-on: [<id>...]            # what this file assumes
refines:    [<id>...]            # what this file makes more precise
related:    [<id>...]            # weakly related, no semantic claim
---
# Title (a complete claim, mirrors the filename)
## One-liner
## Scope
Covered / NOT covered (pointer to where it lives) / what breaks if a `depends-on` assumption fails
## Key concepts
## [Content]
## Agent notes
> Gotcha or cross-reference the reader needs
## Related files
- `<file>` — why relevant (one line, so the agent does not need to open the target)
```

### Step 2c: KB audit (Ralph Loop, max 10 iterations)

**Mechanical first:** run `kb-lint.py` (bundled in this skill's directory; copy it to the
project's `tools/` in Step 2d) and fix every error before spending model time — broken links,
missing frontmatter, oversized files, missing indexes, and properties with no enforcement
channel are machine-findable and machine-verifiably fixed. Only then audit what the machine
cannot:

For each file: gaps? unknowns? contradictions? vague language? rationale blended into a
procedure? glossary terms re-defined outside `kb/GLOSSARY.md`? (kb-lint's W-register and
W-redefine warnings catch the obvious register violations; the model audit catches the rest.)
Structural check: INDEX.md routing valid? cross-references resolve? every dir has INDEX.md?
Fix every CRITICAL finding. Iterate until 0 criticals.

**Exit criterion:**
- Commit the KB. Show summary to user.
- Write 10 difficult questions to `kb/reports/kb-quiz-roundN.md`. Fan out one fresh
  execution-tier (`sonnet`) subagent per question with KB-only access — via the `Workflow`
  tool if the harness provides it, otherwise parallel subagent spawns — so answers don't
  share context. Score the answers in the main session and fix any gap revealed before
  declaring the KB done. (Execution tier on purpose: see Model routing rule 4.)

### Step 2d: Install the usage harness (NOT optional)

A KB that exists but is not routed to is dead weight: future maintenance sessions will grep
the code and never open it, and an unread KB stops being maintained. Before leaving Phase 2,
install the three mechanisms that keep the KB alive after this skill run ends:

1. **CLAUDE.md with the routing protocol.** Create (or merge into) the project `CLAUDE.md`
   from the kit's `templates/claude-md/spec-driven.md`. The "KB routing protocol" section
   MUST be at the top: read `kb/INDEX.md` before any task; update the KB in the same commit
   as any behavior change; on code-vs-KB contradiction, reconcile before building on either.
2. **SessionStart hook.** Merge the kit's `templates/settings/kb-sessionstart.settings.json`
   into the project's `.claude/settings.json` so `kb/INDEX.md` is injected into every
   session's context — presence, not compliance.
3. **kb-lint and ratchet in pre-commit and CI.** Copy `kb-lint.py` and `ratchet.py`
   from this skill's directory to the project's `tools/`, then wire
   `python3 tools/kb-lint.py` and `python3 tools/ratchet.py --from-log <test output>`
   into the project's pre-commit hook and CI pipeline. Both fail the build: lint on a
   KB that drifted, ratchet on a set of passing obligations that shrank. Commit
   `.ratchet.json`. This is the only tier with a hard guarantee — the other two raise
   the probability; this one enforces the invariants.
4. **An inventory of what the harness checks.** One line per check, saying what it
   refuses, under a stated line budget. It is what makes "explain the harness to a
   new engineer" a thing you can actually do, and its growth is the signal that the
   harness is becoming its own engineering problem.

If the kit repo is not available locally, reconstruct the routing protocol from this
section and write kb-lint checks as a project script — the mechanisms matter, not the files.

**The harness is extensible, and extending it is your job.** These three are the KB's
enforcement; they are not the project's. Every time this process produces a rule that
matters — a property, a convention, a premortem tripwire, an ADR consequence, a lesson
learned the hard way in Phase 4 — decide its channel then and there, and write the checker
if one is possible. A `grep` in CI, a hook reading the diff, a counter with a threshold
that fails the build: thirty lines, and the rule stops depending on anyone remembering it.
Do not file this as future work; the rule and its check are one change. When a rule truly
resists checking, write the reason next to it (`none: <reason>` for a property, a line in
the ADR otherwise) — an audit can weigh a stated reason and cannot weigh a silence.

**Exit criterion:** `python3 tools/kb-lint.py kb` exits 0, and a fresh session (or subagent
given only the project directory) demonstrably sees `kb/INDEX.md` without being asked.
