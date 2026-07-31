---
name: audit
description: "Run an autonomous audit-fix loop on the current codebase: detect project type, run the full test suite and linters, fix every failure at the root cause, repeat until green (max 5 iterations). Invoke when the user asks to audit, stabilize, or 'make the tests pass' on an existing project."
---

# Audit Skill

Run an autonomous audit-fix loop on the current codebase.

## When to use

- Whole-codebase stabilization: accumulated test failures, lint debt, "make it green again".
- After a large merge, refactor, or dependency upgrade.

Do NOT use this for reviewing or verifying a single change: Claude Code's built-in
`/code-review` (diff review) and `/verify` (exercise a change end-to-end) cover that.
This skill is the whole-repo convergence loop.

## Process

1. **Detect project type** by checking for `Cargo.toml` (Rust), `pyproject.toml`/`setup.py` (Python), `package.json` (TypeScript/Node).

2. **Run the full test suite:**
   - Rust: `cargo test` + `cargo clippy --all-targets -- -D warnings`
   - Python: `pytest --tb=short -q`
   - TypeScript: `npm test`
   - If a `scripts/validate.sh` exists, use that instead.

3. **For each failing test or lint error:**
   - Diagnose the root cause by reading the relevant source and test files.
   - Apply the minimal fix.
   - Re-run only the affected tests to verify.

4. **After all individual fixes, run the full suite again.**

5. **Repeat until all tests pass or 5 full iterations have been completed.**

6. **After each iteration, report:**
   - Iteration number
   - Tests fixed
   - Tests remaining
   - Systemic issues identified

7. **When done, update `SESSION_STATE.md`** with the audit results.

Work autonomously — do NOT ask for input unless stuck on an ambiguous architectural decision.
