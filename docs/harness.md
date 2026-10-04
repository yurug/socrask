# What this kit's harness checks

Every check, one line each. If this page stops fitting on a screen, or you
cannot hand it to a new engineer and have them tell you what is enforced here,
the harness has become its own engineering problem — which is the failure mode
this page exists to make visible.

`tools/harness-inventory.sh` fails the build when a checker exists that is not
listed here, so the page cannot silently fall behind the machinery.

## Deterministic checks

| Check | What it refuses |
|---|---|
| `skills/spec-driven-dev/kb-lint.py` | a KB that drifts: broken links, missing frontmatter, oversized files, missing indexes, dishonest `last-updated`, and a property that names nothing to enforce it |
| `skills/spec-driven-dev/kb-lint-forebrief.py` | a folded decision whose rationale is not the human's own words, and a questions file competing with the decision log |
| `skills/spec-driven-dev/ratchet.py` | a set of passing obligations that shrinks without a stated reason |
| `skills/spec-driven-dev/resolve-engineering-tool.sh` | an unknown tool name or a false “installed” result when no executable exists in PATH, npm/user bins, or the development checkout |
| `skills/primitives/visual-check.py` | a hand-rolled visual with no marker saying it was not validated |
| `tools/skill-check.py` | invalid public skill metadata, an oversized skill body, a long unindexed reference, or a referenced document that is not shipped |
| `tools/primitives-adoption.sh` | silence about whether the primitives library is actually being used (reports a number, with a threshold that says stop building renderers) |
| `tools/harness-inventory.sh` | a checker that exists but is not on this page |
| `skills/primitives/visual-stop-check.sh` | a session that ends with an artifact and no visual — asks once, and a stated reason closes it (a gate, not a verdict) |
| `tools/ci-local.sh` | nothing itself — it is the runner that gives all of the above one exit code |

| `tools/agent-work.py` | overlapping worktree claims, resource contention, stale handoffs and unaligned integration closure |
| `tools/alignment-check.py` | unresolved declared human checkpoints and stale diff bounds; does not authenticate human evidence |
| `tools/enroll-shared-repo.sh` | tracked/foreign artifact replacement and predictable enrollment conflicts |
| `tools/guard-kit-artifacts.sh` | enrolled personal paths in the index; limited force-add convenience hook |
| `tools/inject-profile.sh` | lifecycle helper: injects only the explicitly enrolled personal profile |
| `tools/outcome-check.py` | incomplete/stale user outcomes, missing cases, erased first-attempt failures, mismatched release/contract and measured regressions |
| `tools/project-check.py` | orphaned commitments, unknown ownership, stale reviews, dependency/WIP violations and closure without matching delivery/acceptance evidence |
| `tools/sync-skills.py` | installation conflicts or missing/drifting selected Claude/Codex skill links (`--check`) |

## Budgets

| Budget | Where it comes from |
|---|---|
| `skills/forebrief/SKILL.md` ≤ 120 lines | forebrief's NF1; the file lives here, so the check does too |
| `templates/claude-md/spec-driven.md` ≤ 120 lines | persistent context carries routing and policy, not a duplicate of the methodology and KB |
| this page ≤ 60 lines | the KISS bound, applied to the thing that lists the checks |

## What the harness does not check

Prose quality, whether a property is the *right* property, whether a decision
was wise, and whether the KB says something true about the world. Those are
audit and human judgment, and no line in this table should be read as covering
them.

| `tools/test-ci-hook.py` | Git hook environment leaking into nested fixture repositories in the actual CI runner |
