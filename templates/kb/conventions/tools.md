---
id: tools
type: constraint
summary: The project's deterministic tools, what each one refuses or produces, and its test.
domain: conventions
last-updated: YYYY-MM-DD
related: [method, code-style, testing-strategy]
---

# Project Tools

## One-liner
The scripts that do this project's rule-following work, so that no agent does it by hand.

## Scope
Covers: the project's own checks, transforms, generators, queries and run commands.
Does NOT cover: the kit's vendored tools (listed in `tools/socrask.json`), and the
language's standard tools, unless the project wraps them.

## Tools

| Tool | Kind | Does | Test |
|---|---|---|---|
| `tools/[name] --check` | [check, transform, generate, query or run] | [what it refuses or produces, in one sentence] | `tools/test-[name]` |

## Agent notes
> Read this table before an operation that follows a rule: a change on many files, a
> derived file, a repeated query or a repeated command sequence. Use the tool when one
> fits. The second time you do an operation by hand, build the tool and add its row in
> the same commit. `tool-check.py` fails a script without a row, and a row without a test
> (or `none: <reason>`).
> Procedure and tool contract: `references/deterministic-tools.md` in the spec-driven-dev skill.

## Related files
- `method.md` -- a method rule enforced by one of these tools cites it in `Enforced-by:`
- `code-style.md` -- a tool is code, and the code rules apply to it
- `testing-strategy.md` -- each tool has unit tests, with the idempotence case
