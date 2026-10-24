# Adopting Socrask by level

A release is not a list of things every project must do. Each kit feature has a
level, and each project adopts what its situation calls for. Adopting a release
takes minutes when nothing in it applies.

## Levels

- **Essential**: every project adopts it, or defers it with a task and a review
  date. Examples: the KB and `kb-lint`, the assumption ledger, plan shape, the
  ratchet, human checkpoints, the writing standard.
- **Triggered**: adopt it when its trigger holds; otherwise record it as
  `not-applicable` with the reason. Examples: the roadmap (more than one slice),
  critical-core kernels (an output with a high cost of error), team
  collaboration (several machines or engineers).
- **Optional**: adopt it if it helps. No record needed.

`python3 tools/kit-adopt.py features` prints the catalogue
(`tools/kit-features.json`): level, release, and trigger or summary for each
feature. Each changelog entry names the level of what it adds.

## Vendor kit files with provenance

```sh
KIT=/absolute/path/to/socrask
python3 "$KIT/tools/kit-adopt.py" vendor kb-lint.py plan-check.py ratchet.py kit-adopt.py kit-features.json
```

The files are copied byte for byte. `tools/socrask.json` records the kit
revision, the tag and each file's hash. Do not edit vendored files: put local
notes in the KB, and send fixes upstream. `kit-adopt.py check` in CI refuses a
vendored file that differs from its hash, and the manifest from before the
rename (`tools/agentic-dev-kit.json`).

## Upgrade at your pace

```sh
python3 "$KIT/tools/kit-adopt.py" status     # changed files and new features since the pin
python3 "$KIT/tools/kit-adopt.py" upgrade    # re-vendor every file from the latest release
```

You do not have to follow every release. Upgrade when a release changes a file
you vendor, adds an essential feature, or adds a triggered feature whose trigger
holds. Then update `kb/work/adoption.json`.

## Record adoption

`kb/work/adoption.json`:

```json
{"kit_tag": "v0.17.0", "features": {
  "ratchet": {"state": "adopted"},
  "roadmap": {"state": "not-applicable", "reason": "one slice so far"},
  "architecture-review": {"state": "deferred", "task": "T-ARCH", "review_on": "2026-11-15"}}}
```

`check` fails in four cases:
- an essential feature marked `not-applicable`;
- a deferral without task or review date;
- a `not-applicable` without reason;
- an adopted feature whose tools are not vendored.

It warns when a deferral passes its review date, and when a feature has no record yet.

## What this does not do

The tool cannot judge whether a trigger holds; the project's record says so, and
review checks the reason. It does not merge local edits into a new release:
that is why local edits are refused.
