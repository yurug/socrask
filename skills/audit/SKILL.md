---
name: audit
description: "Audit an existing codebase or methodology with evidence and prioritized recommendations. Use for whole-project reviews, stabilization, or audit-and-fix requests. Audit is read-only by default; repair only when the user requests it."
---

# Audit

Find defects that affect correctness or the user's stated outcome. Distinguish
reproduced failures from hypotheses and documented limits. Passing the existing
suite does not establish that it tests the right behavior.

Read [the audit policy](references/policy.md) before starting. It defines both
modes and their stopping rules; it also governs the development skill's Phase 5.

1. Identify the requested scope and mode. An audit or request for proposals uses
   **review**; an explicit repair or stabilization request uses **repair**.
2. Read repository instructions, contracts and the real CI entrypoint. Prefer its
   documented command to guessing from the language or package manager.
3. Inspect the risky boundaries and reproduce suspected failures in isolated
   fixtures. Reuse recent validation of unchanged code; run checks that address
   new questions. Do not treat test counts as user-outcome evidence.
4. Report consequential findings with location, trigger, observed result, impact
   and recommended action. Try to refute each serious finding before retaining it.
5. In review mode, deliver findings and stop. Do not edit product code, repair
   failures or create tracking files unless requested.
6. In repair mode, fix verified findings within the authorized scope, add a check
   for the defect class, and re-audit under the policy's shared round budget.

When a finding requires a decision outside the mandate, follow the development
skill's [blocker protocol](../spec-driven-dev/references/blockers.md). Keep
independent investigation moving while the coordinator requests arbitration.
