# Team collaboration across machines and engineers

`tools/agent-work.py` coordinates the agents of one engineer on one machine.
`tools/team-work.py` adds a layer above it, for agents on different machines or
under different engineers. The two layers nest:

- **Team level**: an engineer claims a task and its paths in the shared registry.
  Everyone sees the claim.
- **Inside the claim**: that engineer's agents on one machine split the work
  with `agent-work.py`, as before. `agent-work.py claim --team-task T` refuses a
  local claim outside the paths of team task `T`.

A solo engineer, or a project without a shared remote, uses `agent-work.py` alone.

## Set up the project

1. **Registry.** Nothing to install. The registry is the ref `refs/socrask/registry`
   on the project's Git remote. Anyone with push access can claim.
2. **CI.** A handoff across machines needs a CI result on the exact commit. With
   GitHub, `team-work.py` reads the check runs through `gh`. For another forge, pass
   `--ci-status-cmd` with a command that prints `success`, `failure` or `pending`.
3. **Approvals.** Protect the default branch and require review. A `CODEOWNERS`
   file names who decides for each area.
4. **Shared files.** Add to `.gitattributes`:

   ```gitattributes
   kb/work/meter.jsonl merge=union
   .forebrief/decisions.jsonl merge=union
   ```

   Append-only logs then merge without conflicts. The integration owner alone
   changes the ledger and the shared indexes. Other agents propose those changes
   in their own branch. Run `tools/project-check.py` after every merge.
5. **Kit version.** Write the kit commit to `kb/work/kit-revision`. A claim from
   an agent with another kit revision is refused.

## Work

```sh
KIT=/absolute/path/to/socrask
python3 "$KIT/tools/team-work.py" claim --task T-12 --engineer alice \
  --path src/parser --criteria 'Malformed input is rejected'
python3 "$KIT/tools/team-work.py" renew --task T-12 --engineer alice     # before 4 h
python3 "$KIT/tools/team-work.py" handoff --task T-12 --engineer alice --pr <url>
python3 "$KIT/tools/team-work.py" close --task T-12 --engineer alice \
  --outcome integrated --reason 'Merged after review by the integration owner'
python3 "$KIT/tools/team-work.py" status
```

- **Leases.** A claim lasts four hours unless renewed. An expired claim frees its
  paths. `takeover` with a reason transfers it, and the registry keeps the record.
- **Handoff.** A pull request plus CI `success` on the exact commit. A local run is
  not evidence for another engineer.
- **Integration.** `close --outcome integrated` needs the handoff commit merged into
  the default branch.
- **Audit.** Each registry update is a commit. `git log refs/socrask/registry` shows
  who claimed, renewed, took over and closed what, and when.

## Authority

Each engineer decides for their own area. When a claim covers paths that
`CODEOWNERS` gives to someone else, the claim lists them as `consult`. Decisions in
those paths go to that person, through a forebrief card addressed to them. No agent
answers for another engineer. The integration owner, a named engineer, approves
the combined result through the pull request review.

## What this does not do

- It does not authenticate engineers beyond Git push access. Trust comes from the
  remote's access control.
- It does not correct clock skew. Leases use UTC timestamps from each machine.
- It does not merge code or resolve conflicts. The pull request does that.
- It does not move human checkpoints between engineers. Each engineer runs
  Inbrief and Backbrief for their own work.
