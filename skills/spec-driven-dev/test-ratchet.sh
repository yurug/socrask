#!/bin/sh
# Exercises ratchet.py end to end in a temp dir: it must advance on new passes,
# hold when nothing changes, FAIL when a previously-passing obligation vanishes,
# refuse a retire with no real reason, and accept one with a reason.
#
# The regression case is the whole point of the tool, so it is the one that must
# fail loudly here -- a ratchet that never refuses anything is a counter.
set -eu
cd "$(dirname "$0")"
R="$PWD/ratchet.py"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
S="$tmp/.ratchet.json"
status=0

ok()   { echo "ok   $1"; }
fail() { echo "FAIL $1"; status=1; }

# 1. First run records whatever passes.
if python3 "$R" --state "$S" --passing P1,P2,T3 >/dev/null; then
  ok "first run records 3 obligations"
else
  fail "first run should exit 0"
fi

# 2. Same set again: holds, exit 0.
if python3 "$R" --state "$S" --passing P1,P2,T3 | grep -q "held at 3"; then
  ok "unchanged set holds"
else
  fail "unchanged set should hold at 3"
fi

# 3. A new pass advances the ratchet.
if python3 "$R" --state "$S" --passing P1,P2,T3,P4 | grep -q "advanced to 4"; then
  ok "new pass advances"
else
  fail "new pass should advance to 4"
fi

# 4. THE POINT: P2 disappears -> regression, exit 1, and it names P2.
out=$(python3 "$R" --state "$S" --passing P1,T3,P4 2>&1) && {
  fail "a vanished obligation must exit 1"
} || {
  if echo "$out" | grep -q "REGRESSED P2"; then
    ok "regression is caught and named"
  else
    fail "regression must name P2, got: $out"
  fi
}

# 5. A regression must not be recorded: state still expects P2.
if python3 "$R" --state "$S" --passing P1,P2,T3,P4 | grep -q "held at 4"; then
  ok "a refused run did not advance the state"
else
  fail "state should still hold 4 after a refused run"
fi

# 6. Retiring needs a real reason.
if python3 "$R" --state "$S" --retire P2 --reason "nope" >/dev/null 2>&1; then
  fail "retire with a stub reason must be refused"
else
  ok "retire without a real reason is refused"
fi

# 7. Retiring with a reason drops it, and the drop is on the record.
python3 "$R" --state "$S" --retire P2 \
  --reason "P2 was merged into P4 when the two invariants became one" >/dev/null
if python3 "$R" --state "$S" --passing P1,T3,P4 | grep -q "held at 3"; then
  ok "a retired obligation stops being required"
else
  fail "after retiring P2, the set of three should hold"
fi
if grep -q "merged into P4" "$S"; then
  ok "the retirement reason is recorded in the state"
else
  fail "the reason must be written to the state file"
fi

# 8. Log extraction finds IDs in real-looking test names.
cat > "$tmp/log.txt" <<'LOG'
  ok  "P1: broken citation renders flagged"
  ok  "T-3: hostile filename does not throw"
  ok  "NF2: ready line in under 2s"
LOG
if python3 "$R" --state "$tmp/log.json" --from-log "$tmp/log.txt" | grep -q "NF2, P1, T3"; then
  ok "IDs are extracted from a test log (P-1 and P1 are the same obligation)"
else
  fail "log extraction should find P1, NF2, T3"
fi

exit "$status"
