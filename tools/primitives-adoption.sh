#!/bin/sh
# Primitives adoption metric (backbrief kb/primitives/scope.md, success
# criterion 1; the premortem's most-likely-death tripwire).
#
# The claim it tests: of the first ten agent-produced artifacts after the
# `primitives` skill shipped, at least seven use primitive specs. Below seven,
# STOP BUILDING RENDERERS and fix the authoring friction instead — that is the
# whole point of measuring, and the number is not advisory.
#
# Usage: tools/primitives-adoption.sh [DIR ...]
#   DIR defaults to this repo's own artifact directories. Pass the directories
#   where YOUR generated artifacts land (commonly `kb/reports`), one or more.
#   Deliberately no machine-specific defaults: this script ships in a public
#   kit and must not carry anyone's checkout layout.
#
# Counting rule, deliberately crude and inspectable: an artifact "uses specs"
# if it contains a primitives marker (a spec kind string the renderers emit, or
# an import of the package); it "hand-rolled" if it contains inline <svg> or a
# hand-built table/diagram markup with no marker. An artifact that hand-rolled
# AND carries the unvalidated marker counts as hand-rolled-but-honest, which is
# a different (acceptable) failure than a silent one.
set -eu

DIRS="${*:-}"
if [ -z "$DIRS" ]; then
  # This repo only. Add sibling projects explicitly on the command line.
  root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  DIRS="$root/kb/reports $root/reports $root/research $root/methodology"
fi

total=0
spec=0
handrolled=0
honest=0

for dir in $DIRS; do
  [ -d "$dir" ] || continue
  # Newest first: the metric is about the FIRST ten artifacts after the skill
  # shipped, so review the head of this list against the skill's ship date.
  for f in $(ls -t "$dir"/*.html "$dir"/*.md 2>/dev/null); do
    total=$((total + 1))
    # data-primitive is the renderers' own provenance stamp — added after the
    # first real artifact embedded a spec-rendered SVG and this script counted
    # it as hand-rolled, because nothing in the output said otherwise.
    if grep -qE 'data-primitive="(diagram|filmstrip|chart|matrix|claim)"|primitives/(diagram|filmstrip|chart|matrix|claim)|"kind": *"(diagram|filmstrip|chart|matrix|claim)"' "$f" 2>/dev/null; then
      spec=$((spec + 1))
      printf 'spec        %s\n' "$f"
    elif grep -qE '<svg|<table' "$f" 2>/dev/null; then
      handrolled=$((handrolled + 1))
      if grep -qi 'unvalidated visual' "$f" 2>/dev/null; then
        honest=$((honest + 1))
        printf 'hand-rolled %s  (marked unvalidated — honest)\n' "$f"
      else
        printf 'hand-rolled %s  (UNMARKED — the silent failure)\n' "$f"
      fi
    fi
  done
done

visuals=$((spec + handrolled))
printf '\n%s artifacts scanned, %s contain a visual: %s by spec, %s hand-rolled (%s marked honest)\n' \
  "$total" "$visuals" "$spec" "$handrolled" "$honest"

if [ "$visuals" -lt 10 ]; then
  printf 'Fewer than 10 visual-bearing artifacts yet — the metric is not due.\n'
  exit 0
fi

if [ "$spec" -ge 7 ]; then
  printf 'PASS: %s/10+ use specs.\n' "$spec"
  exit 0
fi

printf 'FAIL: only %s use specs. Per scope.md criterion 1, stop building renderers\n' "$spec"
printf 'and fix the authoring friction (better spec examples, better error paths).\n'
printf 'More instruction is NOT the fix — that was tried and it is what this measures.\n'
exit 1

# BASELINE, 2026-07-27 (the day the skill shipped): 23 artifacts scanned, ZERO
# containing a visual by this script's detection. Worth staring at — across a
# premortem report, an onboarding brief, a research synthesis, several audit
# reports and a card mock, this agent had drawn no diagram, no chart, no
# sequence: only styled prose and card layouts. So the adoption risk is not
# only "hand-rolled instead of spec'd" (what the premortem predicted); it is
# "no visual at all where one would have explained better". A metric reading
# 0/0 is not a pass, and this script cannot tell the difference. Read the head
# of its listing by hand for a while.
