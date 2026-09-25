# Personal enrollment in shared repositories

Run `tools/enroll-shared-repo.sh /path/to/repo --sidecar /outside/repo/personal-kit`.
Git, Python 3 and POSIX file locking are required (Linux/macOS). Paths containing spaces and shell quotes work.
The default sidecar is a sibling directory named `<repo>-kit`.

Enrollment relocates untracked kit artifacts listed in `tools/kit-artifacts.txt`
and creates ignored symlinks to their sidecar content. Existing tracked files,
directories containing tracked files, tracked symlinks, and missing tracked paths
are preserved. Foreign symlinks are left untouched. Conflicting repository and
sidecar content causes a preflight failure, without moving earlier artifacts.
Malformed settings also fail preflight. Unexpected filesystem/I/O errors are not
transactional: inspect the reported paths before retrying.

Untracked, regular `.claude/settings.local.json` settings retain existing values
and receive deduplicated SessionStart and Bash PreToolUse hooks. Tracked settings
(including missing tracked settings), symlinked settings and symlinked `.claude`
directories are preserved; hooks must then be configured manually if wanted.
SessionStart injects `PROFILE.md` from the sidecar. Edit that file for your personal
instructions. The sidecar is not automatically made into a Git repository.

Enrollment uses a repository-wide lock in Git metadata to serialize concurrent
enrollment, including linked worktrees. State publication is atomic for guards.
This lock coordinates enrollment commands, not unrelated Git or filesystem edits.
Use a distinct sidecar per worktree; sharing a sidecar across unrelated repositories
is unsupported.

Enrollment metadata uses Git's per-worktree `--git-path` resolution. Linked
worktrees work, although Git's common `info/exclude` is shared across worktrees.
Repeating enrollment with the same sidecar is safe; changing sidecars is rejected.
An existing team-owned path is skipped, so enrollment does not guarantee every
manifest path is personal or relocated. Review the printed skips.

Before committing, run:

```sh
tools/guard-kit-artifacts.sh --staged /path/to/repo
```

This checks the index for paths owned by that worktree's enrollment, including
personal settings. It fails if those paths appear in the staged diff. It does not
block team-owned paths that enrollment skipped. No Git hooks or global Git
configuration are installed or overridden. The Claude Bash hook also blocks
lexically recognizable direct `git add -f`, `--force`, and bundled force flags,
and refuses Bash calls while personal paths are staged. Reset accidental staging
outside that hook if necessary.

The hook is a convenience guard, not a shell interpreter or security boundary.
Aliases, scripts, other tools, changed enrollment metadata, and commands operating
on other repositories can evade it. Excludes prevent ordinary accidental adds;
the explicit staged check provides a reviewable index check at the time it runs.
Neither offers a universal guarantee against leaks or later index changes.

Run the disposable repository checks with `python3 tools/test-enrollment.py`.
They cover tracked ownership, missing tracked files, foreign symlinks, malformed
settings, preflight conflicts, repeated enrollment, quoted paths, staged leaks,
force flags, concurrent enrollment and linked worktrees.
