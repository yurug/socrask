# Concurrent agents: ownership, evidence, and one human conversation

Use one coordinator and one writing agent per Git worktree. Each worker owns a
bounded slice with acceptance criteria. The coordinator integrates the commits,
runs the combined validation, and owns Inbrief/Forebrief/Backbrief. Workers can
perform read-only reviews without a writing claim. They never answer as the human.

The supplied `tools/agent-work.py` is a POSIX/Python 3 CLI for agents sharing the
**same local Git common directory**, including linked worktrees. Independent
clones, different hosts and network filesystems are not coordinated. The protocol
is agent-neutral; automated Claude session hooks remain a separate integration.

## Start a change

Use absolute paths to the installed kit tools from the project worktrees. Create
a coordinator alignment record following [alignment.md](alignment.md), outside
the committed tree (for example inside the common Git directory). It names the
base SHA, matching coordinator task ID (`work_id`), demand tier, Inbrief disposition and required Backbrief. Do not invent
human completion to start a claim; do independent investigation while it is pending.

```sh
KIT=/absolute/path/to/agentic-dev-kit
BASE=$(git rev-parse HEAD)
ALIGNMENT=/absolute/path/to/this-change-alignment.json
python3 "$KIT/tools/agent-work.py" claim --task integration --owner lead \
  --path docs/release-notes.md --criteria 'Combined regression suite passes' \
  --base "$BASE" --alignment "$ALIGNMENT"

git worktree add -b task/parser ../parser-worktree "$BASE"
cd ../parser-worktree
python3 "$KIT/tools/agent-work.py" claim --task parser --owner agent-a \
  --role worker --coordinator integration --path src/parser --path test/parser \
  --criteria 'Malformed input is rejected; valid fixtures remain accepted'
```

Claims use literal files/directories, not globs. Parent/child path overlaps are
refused atomically, as is a second writing task in the same worktree. Include
associated KB/story files in ownership; give shared indexes to the coordinator.
Never use the same checkout for simultaneous writers. Tool ownership does not
make writes outside the declared scope safe: cooperate with the protocol.

## Validate and hand off

```sh
python3 "$KIT/tools/agent-work.py" check --task parser --owner agent-a
# Commit the bounded change; then validate the exact clean commit.
python3 "$KIT/tools/agent-work.py" run --task parser --owner agent-a \
  --resource browser-port-8994 -- sh tools/test-parser.sh
python3 "$KIT/tools/agent-work.py" handoff --task parser --owner agent-a
```

Resource names are explicit shared identifiers: fixed ports, scratch directories,
external test accounts or deployment targets. Agree the names in the task plan.
`run` acquires all requested resources atomically or fails without running. No
registry lock is held for the duration of tests, so unrelated work can proceed.
Use unique temporary directories/ports where possible instead of serializing.
Never start a second unregistered suite against a registered shared resource.

Handoff requires owned changes, a clean worktree, and the latest command successful
on the current commit. A green command on dirty files cannot certify a later
commit. The command must execute the complete acceptance suite: this tool cannot
know whether `true` or a partial test selection is meaningful evidence. Commands
and exit codes are recorded; stdout/stderr remain on the terminal. Store relevant
logs in the project-approved evidence location without secrets.

Ready tasks retain their path claims. The coordinator merges their commits (not
an unrelated squash whose ancestry loses the recorded evidence), then runs its
combined acceptance command. Its allowed integration scope includes owned paths
of associated ready workers **only once their handoff commits are ancestors of
its HEAD**. It then hands off the combined commit and runs the final Backbrief.

```sh
# In the coordinator worktree, after merging the ready worker branches:
python3 "$KIT/tools/agent-work.py" run --task integration --owner lead \
  --resource full-ci -- sh tools/ci-local.sh
python3 "$KIT/tools/agent-work.py" handoff --task integration --owner lead
# Complete the actual human checkpoint and update ALIGNMENT for this exact HEAD.
python3 "$KIT/tools/agent-work.py" close --task integration --owner lead \
  --outcome integrated --alignment "$ALIGNMENT" \
  --reason 'Combined commit validated; human checkpoint evidence recorded'
# Each worker can then close from its own unchanged handoff worktree:
python3 "$KIT/tools/agent-work.py" close --task parser --owner agent-a \
  --outcome integrated --reason 'Included in the coordinator integration commit'
```

A technical handoff is not human closure. Pending Backbrief blocks integrated
closure, not independent testing or another unrelated slice. `degraded-authorized`
requires an actual human authorization reference. A changed HEAD needs new testing
and a fresh handoff; ready tasks are immutable in this first version, so close the
attempt as abandoned and claim a new task ID for revisions. Keep the old record.

## Interruption and recovery

`status` prints task ownership, checks and active resource leases as JSON. Claims
never expire automatically; a slow agent must not lose its files to a timer.
`close --outcome abandoned --reason '...'` releases a task only when it has no
running command. An abandoned task is not integrated or human-approved.

A child waits on a pipe until its resource lease is persisted before executing the
requested command. If the supervisor dies first, EOF prevents execution. If it
dies during execution, leases remain. Commands must not daemonize or escape their
process group. A surviving descendant keeps the lease after the leader exits.
After confirming the supervisor and its entire recorded process group are gone:

```sh
python3 "$KIT/tools/agent-work.py" recover-task --task parser \
  --reason 'Interrupted test supervisor and process group have both stopped'
```

Recovery refuses live processes and records a failed check; it never certifies
completion. A reused PID conservatively prevents recovery. Detached descendants,
manual Git writes and forged alignment JSON are outside enforcement. This is a
coordination harness for cooperating agents, not an OS sandbox or identity system.
Registry files live under Git's common directory in `agentic-loop/`, with `flock`
and atomic replacement. Do not copy the registry between clones or commit it.
