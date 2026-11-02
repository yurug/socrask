# Deterministic tools

## Contents

- [Why a tool, not a model](#why-a-tool-not-a-model)
- [Kinds of tool](#kinds-of-tool)
- [When to build one](#when-to-build-one)
- [The tool contract](#the-tool-contract)
- [How to use one](#how-to-use-one)
- [The catalog](#the-catalog)
- [What is not checked](#what-is-not-checked)

## Why a tool, not a model

A model writes tools well and runs procedures badly. An agent that applies one edit
to forty files by hand can skip a file or vary the edit. The reviewer then has forty
sites to read, and the next run costs the same tokens again. A script applies the
edit the same way at each site. The reviewer reads its rule once, and the next run
costs nothing. Use the model for judgment, and a tool for every operation that
follows a rule.

"Enforce, don't request" makes a check of each rule that must hold. This reference
extends it to the work itself: each operation that follows a rule is done by a tool.

## Kinds of tool

| Kind | What it does | Examples |
|---|---|---|
| `check` | refuses a state, with an exit code | a lint rule, a budget, a schema check |
| `transform` | changes code or data by a rule | a codemod, a rename, a format migration |
| `generate` | writes a file from a source of truth | bindings from a schema, tables from data |
| `query` | answers a question about the code | callers of a function, sites of a pattern |
| `run` | runs a procedure in one command | build, test one property, reset fixtures |

## When to build one

- **A mechanical change on more than five files.** Write the transform, run it, and
  review it. Do not edit the files one by one.
- **The second time.** The second time an agent does the same operation or the same
  sequence of commands by hand, it builds the tool. The first time, it writes the
  operation in the task notes, so that the second time is visible.
- **A derived file.** A file computed from another (a table, a binding, a type from a
  schema) comes from a generator; nobody edits it. The generator's `--check` mode fails when the
  committed file is stale (`roadmap-check.py --write` is an example).
- **A repeated question.** When agents explore the code twice for the same answer,
  write the query.

Use an existing tool first: the compiler, the formatter, an LSP rename, `ast-grep`,
`semgrep`, `comby`, or the language's codemod library. Write a new tool only when
none fits.

Do not build a tool for a one-off change that a reviewer can read in one diff. Do not
build one for an operation that needs a judgment at each site. There, the query tool
lists the sites, and the model decides each one.

## The tool contract

A tool is code, so the [code rules](implementation-and-audits.md) apply to it. Each
tool also follows this contract:

1. **Deterministic.** The same inputs give the same output. Pass the clock,
   randomness and network in explicitly, or do not use them.
2. **Idempotent.** A second run changes nothing. A transform that runs on its own
   output is a no-op; a test proves it.
3. **A check mode.** `--check` (or a dry run) changes nothing and exits non-zero when
   the tool would change something. That mode makes each generator and transform its
   own staleness gate.
4. **Errors that an agent can act on.** Each error gives a stable code, the location
   and the fix: `E-stale: kb/roadmap.md: run roadmap-check.py --write`.
5. **Quiet, stable output.** Each run lands in an agent's context, so output is a
   cost. On success, print one summary line. Group repeated findings by code, with a
   flag (`--all`) that lists them. A read command prints one line per entry and
   filters before it prints. Output that a script reads has a stable format.
6. **A header that stands alone.** The file header states the purpose, the usage and
   the exit codes. It lists the cases that the tool checks or changes, and what it does not do.
7. **Unit tests.** One test per case of the contract, with the idempotence case, in
   `test-<tool>` beside it.
8. **Least authority.** The tool touches only the paths that it receives. It never
   commits, pushes, or deletes outside them.

## How to use one

- **Run it, then review it.** Review the tool's rule, the diff summary and a sample of
  the sites. Run the tests as usual.
- **One commit per run.** Commit a transform's result alone, with the command in the
  message: `transform: <command>`. A reviewer can run it again and compare.
- **In the plan.** A mechanical step is an execution step. Its Files name the tool;
  its Acceptance runs the tool's `--check` mode and the tests.
- **In the loop.** When a check fails the same way on many sites, fix it with a
  transform, not with one repair per site.
- **Through its interface, not its data.** When a tool owns a data file, such as the
  work ledger and `ledger.py`, read and change the file through the tool. Do not load
  the file into context, and do not write a script against it.

## The catalog

`kb/conventions/tools.md`, from `templates/kb/conventions/tools.md`, lists each tool
of the project in one table:

| Column | Content |
|---|---|
| Tool | the path, or the command, in backticks |
| Kind | `check`, `transform`, `generate`, `query` or `run` |
| Does | what it refuses or produces, in one sentence |
| Test | the test path, or `none: <reason>` |

An agent reads the catalog before it starts an operation that follows a rule.
`tool-check.py` runs in CI:

```sh
python3 tools/tool-check.py kb/conventions/tools.md --dir tools
```

It fails when the catalog does not list a script of a tool directory. It also fails
on a row with a missing path, an unknown kind, or a missing test. It skips the kit files listed in `tools/socrask.json`.

## What is not checked

`tool-check.py` checks the catalog against the tool directories. It cannot see that
an agent edited forty files by hand, and it cannot tell whether a tool is
deterministic. The Phase 5 review asks the first question. The milestone
retrospective asks which operation the agents repeated by hand.
