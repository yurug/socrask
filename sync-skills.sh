#!/bin/bash
# Install agentic-loop-kit skills into the global Claude Code skills directory.
#
# Skills are symlinked (not copied) so the repo stays the single source of
# truth: editing a skill in the repo is immediately live, and drift between
# the repo and ~/.claude/skills is structurally impossible.
#
# Claude Code discovers skills as directories: ~/.claude/skills/<name>/SKILL.md
# (flat .md files are ignored). Symlinked directories are supported.
# Idempotent: safe to re-run after adding or renaming skills.

set -euo pipefail

SKILLS_SRC="$(cd "$(dirname "$0")/skills" && pwd)"
SKILLS_DST="$HOME/.claude/skills"

mkdir -p "$SKILLS_DST"

# Link every skill directory from the repo.
for src in "$SKILLS_SRC"/*/; do
  name=$(basename "$src")
  [ -f "$src/SKILL.md" ] || { echo "SKIP $name (no SKILL.md)"; continue; }
  dst="$SKILLS_DST/$name"
  if [ -L "$dst" ]; then
    if [ "$(readlink -f "$dst")" = "$(readlink -f "$src")" ]; then
      echo "OK   $name"
      continue
    fi
    echo "FIX  $name (symlink pointed elsewhere: $(readlink "$dst"))"
    rm "$dst"
  elif [ -e "$dst" ]; then
    echo "WARN $name exists in $SKILLS_DST as a real file/dir — resolve manually:"
    echo "     diff -r '$dst' '${src%/}'"
    continue
  else
    echo "LINK $name"
  fi
  ln -s "${src%/}" "$dst"
done

# Report entries in ~/.claude/skills that the repo doesn't know about.
for dst in "$SKILLS_DST"/*; do
  [ -e "$dst" ] || continue
  name=$(basename "$dst")
  if [ ! -d "$SKILLS_SRC/$name" ]; then
    echo "ORPHAN $name (not from this repo; left untouched)"
  fi
done

echo "Done. Skills link into $SKILLS_SRC"
