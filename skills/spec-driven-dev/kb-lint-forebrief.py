#!/usr/bin/env python3
"""kb-lint-forebrief — the verbatim-rationale check (P7).

forebrief's fold-in contract (ADR-005-fold-in-contract.md) requires that a
folded KB file never lose a decision's rationale or ask-why exchange in
translation. `kb-lint.py` itself stays generic and unaware of forebrief;
this is a STANDALONE companion script wired into the same pre-commit/CI
line, gated on forebrief actually being present in the host repo.

Activation: does nothing (exit 0) unless `<REPO_ROOT>/.forebrief/
decisions.jsonl` exists — a repo with no forebrief session has nothing for
this check to verify.

For every `*.md` file under KB_DIR carrying a `forebrief-record:`
frontmatter key (a scalar card ulid, a `[a, b, c]` list of them, or a
`seq:<n>` reference to a cardless decision — forebrief ADR-009):

  - every `decision`/`reconciliation` record tied to that card must have its
    `rationale` appear VERBATIM (whitespace-normalized, blockquote markers
    stripped) somewhere in the file body — no link escape hatch for
    rationale, ever (config-and-formats.md).
  - every `ask_why`/`answer` record tied to that card must have its `text`
    appear verbatim OR the file must contain a `forebrief:record:<seq>` link
    resolving to ANY record in that card's own ask_why/answer thread (one
    link covers the whole thread, config-and-formats.md's "by link" escape
    hatch — not a per-message accounting).

Also (the routing tripwire, task item 5c): warns -- never errors -- on any
`kb/questions-round*.md` file whose last commit is newer than
`.forebrief/decisions.jsonl`'s FIRST record. That combination means someone
kept hand-writing ambiguity-round markdown after forebrief was already
logging decisions for this repo -- spec-driven-dev's Phase 1 routing flip
(post cards instead) isn't being followed. A warning, not an error: it is a
process signal for a human to notice, not a defect in the folded KB itself.

Usage:
    kb-lint-forebrief.py [KB_DIR]

    KB_DIR  defaults to ./kb; the repo root is KB_DIR's parent directory
            (mirrors kb-lint.py's own `kb-lint.py kb` calling convention).

Exit code: 0 = clean or inactive (warnings allowed), 1 = a verbatim-rationale
violation found.
"""

import datetime
import json
import os
import re
import subprocess
import sys

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
LINK_RE = re.compile(r"forebrief:record:(\d+)")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?", re.MULTILINE)


def parse_frontmatter(text):
    """Return the `forebrief-record` frontmatter value as a list of ids, or []."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return []
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.strip() != "forebrief-record":
            continue
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            return [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        value = value.strip("'\"")
        return [value] if value else []
    return []


def normalize(text):
    """Whitespace-normalize (and blockquote-strip) so wrapping/quoting in
    the folded prose never causes a false E-verbatim positive — the
    mitigation plan.md step 4 named for the check's "biggest unknown"."""
    text = BLOCKQUOTE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def load_records(decisions_log_path):
    """@returns (records_by_card, all_seqs, first_ts) -- records_by_card maps
    a card id to its list of {seq, type, payload} dicts, in log order;
    first_ts is the log's first (lowest-seq) envelope timestamp, or None."""
    records_by_card = {}
    all_seqs = set()
    first_ts = None
    with open(decisions_log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                envelope = json.loads(line)
            except json.JSONDecodeError:
                continue  # a torn final line is core's own concern, not this check's
            if first_ts is None:
                first_ts = envelope.get("ts")
            all_seqs.add(envelope.get("seq"))
            payload = envelope.get("payload", {})
            card = payload.get("card")
            if card is None:
                # A cardless decision (forebrief ADR-009): a decision reached
                # about something nobody carded, carrying its own prompt. It has
                # no card id to key on, which is exactly why its rationale was
                # recorded but not gate-protected — the gap ADR-009 named as its
                # own next question. Key it by `seq:<n>` instead: the log already
                # uses that identity for the thread link form
                # (`forebrief:record:<seq>`), so a folded file anchors on
                # `forebrief-record: seq:41` with no new concept.
                if envelope.get("type") == "decision" and payload.get("prompt"):
                    key = f"seq:{envelope.get('seq')}"
                    records_by_card.setdefault(key, []).append(
                        {
                            "seq": envelope.get("seq"),
                            "type": envelope.get("type"),
                            "payload": payload,
                        }
                    )
                continue
            records_by_card.setdefault(card, []).append(
                {"seq": envelope.get("seq"), "type": envelope.get("type"), "payload": payload}
            )
    return records_by_card, all_seqs, first_ts


def parse_iso(ts):
    """Tolerant ISO-8601 parse (accepts a trailing 'Z'); None on anything else."""
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def git_commit_datetime(repo_root, relpath):
    """@returns the last commit's ISO-8601 author date for relpath, or None
    (not in git, or git unavailable -- the caller falls back to mtime)."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", relpath],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    return parse_iso(out.stdout.strip()) if out.stdout.strip() else None


def check_routing_tripwire(repo_root, scan_roots, first_ts, warnings):
    """W-routing (task item 5c): a questions-round*.md file committed (or, if
    still untracked, last modified) AFTER forebrief's first logged decision
    means the Phase 1 routing flip to posting cards isn't being followed."""
    first_dt = parse_iso(first_ts)
    if first_dt is None:
        return
    for scan_root in scan_roots:
      for root, dirs, names in os.walk(scan_root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in names:
            if not re.match(r"questions-round.*\.md$", name):
                continue
            full = os.path.join(root, name)
            rel_to_repo = os.path.relpath(full, repo_root)
            file_dt = git_commit_datetime(repo_root, rel_to_repo)
            if file_dt is None:
                try:
                    file_dt = datetime.datetime.fromtimestamp(
                        os.path.getmtime(full), tz=datetime.timezone.utc
                    )
                except OSError:
                    continue
            if file_dt > first_dt:
                rel = os.path.relpath(full, repo_root)
                warnings.append(
                    (
                        rel,
                        "W-routing: newer than forebrief's first logged decision -- "
                        "forebrief-enabled repos should post cards (spec-driven-dev "
                        "Phase 1's routing flip), not write question-round markdown",
                    )
                )


def check_rationale(card_id, records, body_normalized, errors, rel):
    for r in records:
        if r["type"] not in ("decision", "reconciliation"):
            continue
        rationale = r["payload"].get("rationale")
        if not rationale:
            continue  # T3: an override may legally commit with no rationale
        if normalize(rationale) not in body_normalized:
            errors.append(
                (rel, f"E-verbatim: card {card_id} seq {r['seq']} rationale not found verbatim")
            )


def check_thread(card_id, records, body_normalized, link_seqs, errors, rel):
    thread = [r for r in records if r["type"] in ("ask_why", "answer")]
    if not thread:
        return
    thread_seqs = {r["seq"] for r in thread}
    if thread_seqs & link_seqs:
        return  # one resolvable link covers the WHOLE thread (config-and-formats.md)
    for r in thread:
        text = r["payload"].get("text", "")
        if normalize(text) not in body_normalized:
            errors.append(
                (
                    rel,
                    f"E-verbatim: card {card_id} seq {r['seq']} ({r['type']}) text not found "
                    "verbatim, and no forebrief:record link resolves to this thread",
                )
            )


def fold_target_dirs(repo_root):
    """Scan roots for folded files, from .forebrief/config.json's foldIn block.

    Dogfooding gap 2 (2026-07-26): this used to hardcode `kb`, so a repo whose
    fold targets live elsewhere (the agentic-loop-kit folds into `methodology/`)
    got NO verbatim checking at all -- silently, which is the worst way for a
    gate to be absent. Targets now come from the same config the fold itself
    reads, so the two can never disagree.
    """
    cfg_path = os.path.join(repo_root, ".forebrief", "config.json")
    dirs = []
    try:
        with open(cfg_path, encoding="utf-8") as f:
            fold_in = (json.load(f) or {}).get("foldIn") or {}
        for key in ("adrDir", "roundsDir"):
            value = fold_in.get(key)
            if isinstance(value, str) and value:
                dirs.append(value)
    except (OSError, ValueError):
        pass
    if not dirs:
        dirs = ["kb"]
    # de-duplicate while keeping the shallowest ancestor: kb/architecture/decisions
    # under kb/ would otherwise be walked twice and double-count `checked`.
    roots = []
    for d in sorted({os.path.normpath(x) for x in dirs}, key=len):
        abs_d = os.path.abspath(os.path.join(repo_root, d))
        if not any(abs_d == r or abs_d.startswith(r + os.sep) for r in roots):
            roots.append(abs_d)
    return roots


def main():
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    if explicit:
        kb_dir = os.path.abspath(explicit)
        repo_root = os.path.dirname(kb_dir)
        scan_roots = [kb_dir]
    else:
        repo_root = os.path.abspath(".")
        scan_roots = fold_target_dirs(repo_root)
        kb_dir = scan_roots[0]
    log_path = os.path.join(repo_root, ".forebrief", "decisions.jsonl")

    if not os.path.isfile(log_path):
        print("kb-lint-forebrief: no .forebrief/decisions.jsonl -- not forebrief-enabled, skipping")
        return 0
    existing = [d for d in scan_roots if os.path.isdir(d)]
    if not existing:
        shown = ", ".join(os.path.relpath(d, repo_root) for d in scan_roots)
        print(f"kb-lint-forebrief: no fold target directory exists ({shown})", file=sys.stderr)
        return 2
    scan_roots = existing

    records_by_card, all_seqs, first_ts = load_records(log_path)
    errors = []
    warnings = []
    checked = 0
    check_routing_tripwire(repo_root, scan_roots, first_ts, warnings)

    for scan_root in scan_roots:
      for root, dirs, names in os.walk(scan_root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in sorted(names):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, repo_root)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            card_ids = parse_frontmatter(text)
            if not card_ids:
                continue
            checked += 1
            body_normalized = normalize(BLOCKQUOTE_RE.sub("", text))
            link_seqs = {int(m) for m in LINK_RE.findall(text)} & all_seqs
            for card_id in card_ids:
                records = records_by_card.get(card_id, [])
                check_rationale(card_id, records, body_normalized, errors, rel)
                check_thread(card_id, records, body_normalized, link_seqs, errors, rel)

    for rel, msg in errors:
        print(f"ERROR {rel}: {msg}")
    for rel, msg in warnings:
        print(f"WARN  {rel}: {msg}")
    print(
        f"kb-lint-forebrief: {checked} forebrief-record file(s) checked, "
        f"{len(errors)} errors, {len(warnings)} warnings"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
