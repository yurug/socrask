#!/usr/bin/env python3
"""kb-lint — mechanical validation for agent-optimized knowledge bases.

The KB methodology (see spec-driven-dev) rests on properties that are
machine-checkable: files stay small, frontmatter triages, links resolve,
indexes route. This linter turns "the KB is maintained" from a hope into
an exit code. Wire it into pre-commit and CI; errors fail the build.

Usage:
    kb-lint.py [KB_DIR] [--strict] [--no-git] [--required-keys k1,k2,...]

    KB_DIR            defaults to ./kb
    --strict          treat warnings as errors
    --no-git          skip git-based staleness checks
    --required-keys   override the required frontmatter keys
                      (use "id,domain,last-updated" for pre-2026 KBs
                      that lack type/summary)

Exit code: 0 = clean (warnings allowed), 1 = errors (or warnings with --strict).

Checks (E = error, W = warning):
    E-frontmatter   missing or unparseable frontmatter block
    E-key           missing required frontmatter key
    E-type          `type` not in the closed set
    E-date          `last-updated` not a real YYYY-MM-DD date
    E-dup-id        duplicate `id` across the KB
    E-link          markdown/backtick link to a KB .md path that does not exist
    E-id-ref        depends-on/refines/related names an id that no file declares
    E-length        file exceeds max lines (default 200; override with
                    `lint-max-lines: N` in frontmatter, which documents the
                    exception where reviewers will see it)
    E-index         directory holding 2+ md files has no INDEX.md
    E-unenforced    a property under properties/ (P<n>/NF<n>/T<n>, written as a
                    heading, a bullet, or a table row) that declares no
                    `Enforced-by:` channel — for a table, that means the table
                    has no `Enforced-by` column
    E-channel       `Enforced-by:` names a channel outside the closed set, or
                    names a file that does not exist. The set, strongest first:
                    structural | proof | test | mechanical | hook | none
    W-trust         a `proof:` channel whose property never says what the proof
                    leaves out (statement, boundary, kernel)
    E-noreason      `Enforced-by: none:` with no real reason after the colon
    W-stale         last git commit of the file is newer than `last-updated`
    W-dirty         file has uncommitted changes but `last-updated` is not today
    W-orphan        no other file links to this one (unreachable from the graph)
    W-bare-link     bare-filename backtick ref that resolves nowhere
    W-register      rationale-shaped section header (why/rationale/motivation/
                    background/justification) in a `procedure` file — the why
                    belongs in an ADR that the procedure links
    W-redefine      a glossary term re-defined outside the glossary file
                    (define once; content files link the glossary instead)
    W-unenforced    a `constraint` file outside properties/ that shouts a
                    binding rule (MUST/NEVER) and names no channel

Exempt from all checks (but still valid link targets): reports/ (generated
artifacts) and questions-round*.md (working files edited by the user).
"""

import argparse
import datetime
import os
import re
import subprocess
import sys

TYPE_SET = {"concept", "decision", "constraint", "procedure", "spec",
            "external", "index", "glossary"}
DEFAULT_REQUIRED = ["id", "type", "summary", "domain", "last-updated"]
DEFAULT_MAX_LINES = 200
ID_REF_KEYS = ("depends-on", "refines", "related")

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`\s]+\.md(?:#[^`]*)?)`")
FENCE_RE = re.compile(r"^(```|~~~)", re.MULTILINE)
RATIONALE_HEADER_RE = re.compile(
    r"^#{2,6}\s+(?:why\b|rationale\b|motivation\b|background\b|justification\b)"
    r"[^\n]*", re.IGNORECASE | re.MULTILINE)
# Matches the glossary's own definition shape: `- **Term**: ...`. Terms holding
# placeholder characters ([, <, *) are template scaffolding, not definitions.
TERM_DEF_RE = re.compile(r"^\s*-\s+\*\*([^*\[\]<>]+)\*\*\s*:", re.MULTILINE)

# -- Enforcement channels. A property says what must hold; `Enforced-by:` names
# the machinery that holds it. `instruction` is deliberately NOT a channel:
# prose in a CLAUDE.md raises a probability, and admitting it here would let
# every property pass by pointing at a paragraph — which is the exact defect
# this check exists to catch. When prose really is all there is, the honest
# declaration is `none: <reason>`, and the reason is what a later audit reads.
# Real KBs write a claim in one of three shapes — a heading, a bullet, or a
# table row — and a checker that reads only headings reports "clean" on the
# other two, which is worse than not checking at all.
CLAIM_ID = r"(?:P|NF|T)-?\d+"
CLAIM_HEADING_RE = re.compile(rf"^#{{2,6}}\s+\**({CLAIM_ID})\b")
CLAIM_BULLET_RE = re.compile(rf"^(\s*)[-*]\s+\**({CLAIM_ID})\**\s*[:.—–-]?\s")
BULLET_RE = re.compile(r"^(\s*)[-*]\s")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
ENFORCED_COL_RE = re.compile(r"enforced.?by", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
# Searched, not anchored: the line may be a nested bullet, a bold run, or the
# tail of the claim's own sentence. The lookbehind keeps prose that *names* the
# field in backticks (as this kit's own templates do) from parsing as one.
ENFORCED_RE = re.compile(r"(?<!`)\bEnforced-by\**\s*:\s*(.+)$", re.IGNORECASE)
EMPTY_CELL = ("", "-", "--", "—", "–", "n/a")
# Ordered strongest-first, and the order is the recommendation: a wrong answer
# that cannot be represented beats one that is merely caught, and a proof says
# "for every input" where a test says "not for these". `structural:` names the
# type, capability, or construction that makes the violation unrepresentable;
# `proof:` names a machine-checked obligation, and the property is expected to
# name what the proof does NOT cover (statement, boundary, kernel) -- an
# unnamed trust boundary is what separates a guarantee from a slogan.
CHANNELS = ("structural", "proof", "test", "mechanical", "hook", "none")
# Same threshold as skills/primitives/visual-check.py's no-visual reason, on purpose: the
# two gates make the same demand ("a reason has to be a reason") and must not
# drift into disagreeing about what counts as one.
MIN_REASON = 20
# Uppercase only. Lowercase "must" is ordinary prose; the shouted form is how
# this methodology writes a binding rule, so it is the form worth holding to a
# channel.
BINDING_RE = re.compile(r"\b(?:MUST NOT|MUST|NEVER|SHALL)\b")
# What a proof does not cover has to be written next to what it does. A proof is
# universal over the property AS STATED, under the assumptions its kernel and
# extraction carry; a property that names none of that reads as a guarantee over
# the whole system, which is the one thing it is not.
TRUST_RE = re.compile(
    r"^\s*[-*>]?\s*\**(?:trusted|trust boundary|not covered|does not cover|"
    r"assumes|assumptions)\**\s*:", re.IGNORECASE)


def is_exempt(relpath):
    parts = relpath.split(os.sep)
    return parts[0] == "reports" or \
        re.match(r"questions-round.*\.md$", parts[-1]) is not None


def parse_frontmatter(text):
    """Return (dict, error). Naive YAML: `key: scalar` and `key: [a, b]` only."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "no frontmatter block (file must start with ---)"
    fm = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return fm, None
        line = line.split("#", 1)[0].rstrip()  # strip trailing comments
        if not line.strip():
            continue
        if ":" not in line:
            return None, f"frontmatter line {i + 1} is not `key: value`"
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            fm[key] = [v for v in items if v]
        else:
            fm[key] = value.strip("'\"")
    return None, "frontmatter block never closed with ---"


def strip_fences(text):
    """Blank out fenced code blocks so example paths inside them are not linted."""
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append("")
        else:
            out.append("" if in_fence else line)
    return "\n".join(out)


def extract_links(text):
    """Yield (target, bare) for every KB-file reference in prose.

    Globs (`spec/*.md`) and placeholders (`<name>.md`, `YYYY-MM-DD`) are
    patterns, not links — skip them rather than flag them.
    """
    def is_pattern(t):
        return any(c in t for c in "*<>") or "YYYY" in t

    body = strip_fences(text)
    for m in MD_LINK_RE.finditer(body):
        t = m.group(1).split("#", 1)[0].strip()
        if t and not t.startswith(("http://", "https://", "mailto:")) \
                and t.endswith(".md") and not is_pattern(t):
            yield t, False
    for m in BACKTICK_RE.finditer(body):
        t = m.group(1).split("#", 1)[0].strip()
        if t and not t.startswith(("http://", "https://")) and not is_pattern(t):
            # A bare filename (`INDEX.md`) is a weaker claim than a path.
            yield t, "/" not in t


def git_dates(kb_dir, relpath):
    """Return (last_commit_date, is_dirty) or (None, None) if not in git."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=short", "--", relpath],
            cwd=kb_dir, capture_output=True, text=True, timeout=10)
        commit = out.stdout.strip() or None
        st = subprocess.run(
            ["git", "status", "--porcelain", "--", relpath],
            cwd=kb_dir, capture_output=True, text=True, timeout=10)
        return commit, bool(st.stdout.strip())
    except Exception:
        return None, None


def declared_channels(region):
    """Every `Enforced-by:` value stated anywhere in a claim's region.

    A wrapped value is one value: a `none:` reason that runs onto the next line
    is still a reason, and truncating at the line break would fail exactly the
    authors who wrote a long enough one.
    """
    values, i = [], 0
    while i < len(region):
        m = ENFORCED_RE.search(region[i])
        if not m:
            i += 1
            continue
        parts, i = [m.group(1).strip()], i + 1
        while i < len(region):
            nxt = region[i]
            # A following field label ends the value. Without this, the
            # `Trusted:` line a proof channel is REQUIRED to carry gets joined
            # onto the channel and turns a correct declaration into E-channel.
            if not nxt.strip() or HEADING_RE.match(nxt) or TABLE_ROW_RE.match(nxt) \
                    or BULLET_RE.match(nxt) or ENFORCED_RE.search(nxt) \
                    or TRUST_RE.match(nxt):
                break
            parts.append(nxt.strip())
            i += 1
        # `*Enforced-by:* test:...` and `**Enforced-by:**  test:...` are how this
        # gets written in files that mark their field labels, so the emphasis
        # that lands on the value side is stripped rather than parsed as a channel.
        values.append(" ".join(parts).rstrip("|").strip().lstrip("*_` ").strip())
    return values


def heading_claims(lines):
    """Claims written as headings. A claim owns everything down to the next
    heading at its level or above, so a nested `#### Violation example` block
    still belongs to it and a channel placed anywhere under it counts."""
    heads = []                      # (line index, level, claim id or None)
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            claim = CLAIM_HEADING_RE.match(line)
            heads.append((i, len(m.group(1)), claim.group(1) if claim else None))
    for pos, (i, level, claim) in enumerate(heads):
        if claim:
            end = next((j for j, lvl, _ in heads[pos + 1:] if lvl <= level),
                       len(lines))
            region = lines[i + 1:end]
            yield claim, i + 1, declared_channels(region), None, region


def bullet_claims(lines):
    """Claims written as list items (`- **T1** ...`). The region runs to the
    next bullet at the same indent or shallower, so nested detail lines count."""
    i = 0
    while i < len(lines):
        m = CLAIM_BULLET_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent, end = len(m.group(1)), i + 1
        while end < len(lines):
            nxt = BULLET_RE.match(lines[end])
            if HEADING_RE.match(lines[end]) or (nxt and len(nxt.group(1)) <= indent):
                break
            end += 1
        region = lines[i:end]
        yield m.group(2), i + 1, declared_channels(region), None, region
        i = end


def table_claims(lines):
    """Claims written as table rows, where the channel is a column. A table of
    claims with no `Enforced-by` column declares nothing for any of its rows."""
    def cells(line):
        return [c.strip() for c in line.strip().strip("|").split("|")]

    i = 0
    while i < len(lines):
        if not TABLE_ROW_RE.match(lines[i]):
            i += 1
            continue
        start = i
        while i < len(lines) and TABLE_ROW_RE.match(lines[i]):
            i += 1
        block = lines[start:i]
        if len(block) < 3:          # header, separator, at least one row
            continue
        header = cells(block[0])
        col = next((k for k, h in enumerate(header) if ENFORCED_COL_RE.search(h)),
                   None)
        for off, row in enumerate(block[2:], start=2):
            row_cells = cells(row)
            claim = row_cells[0].strip("*` ") if row_cells else ""
            if not re.fullmatch(CLAIM_ID, claim):
                continue
            value = row_cells[col].strip() if col is not None \
                and col < len(row_cells) else ""
            values = [] if value.lower() in EMPTY_CELL else [value]
            hint = None if col is not None else \
                " — this table has no `Enforced-by` column; add one"
            yield claim, start + off + 1, values, hint, [row]


def find_claims(body):
    """Yield (claim_id, line_no, channels, hint, region) for every claim.

    One shape per file, in priority order: if it states claims as headings, a
    claim-shaped bullet in a "Related" list is not a second claim. Falling back
    only when the richer shape is absent keeps a file's summary table from
    being read as a duplicate set of claims with different rules.
    """
    lines = body.splitlines()
    for shape in (heading_claims, bullet_claims, table_claims):
        found = list(shape(lines))
        if found:
            return found
    return []


def check_channel(value, kb):
    """Return (code, message) for a bad `Enforced-by:` value, else None."""
    channel, _, detail = value.partition(":")
    channel, detail = channel.strip().lower(), detail.strip()
    if channel not in CHANNELS:
        hint = ""
        if channel == "instruction":
            hint = (" — prose only raises a probability; if that is genuinely all "
                    "there is, say `none: <reason>` and let the audit read the reason")
        return ("E-channel",
                f"`{channel or value}` is not a channel {list(CHANNELS)}{hint}")
    if channel == "none":
        if len(detail) < MIN_REASON:
            return ("E-noreason",
                    f"`none:` needs an actual reason (>= {MIN_REASON} chars), "
                    f"got `{detail}`")
        return None
    if not detail:
        return ("E-channel",
                f"`{channel}:` names nothing — give the file that does the enforcing")
    # `tests/sync.test.ts::P4` and `tools/kb-lint.py#E-channel` both point at a
    # file plus a location inside it; only the file part is checkable here.
    path = re.split(r"::|#", detail, maxsplit=1)[0].strip()
    if any(c in path for c in "*<>"):
        return None                 # a template placeholder, not a claim about a file
    cands = [os.path.join(kb, "..", path), os.path.join(kb, path)]
    if not any(os.path.exists(os.path.normpath(c)) for c in cands):
        return ("E-channel", f"`{path}` does not exist — a channel that names a "
                             "missing file enforces nothing")
    return None


def check_enforcement(rel, body, fm, kb, errors, warnings):
    """Every property names the machinery that enforces it.

    Hard inside properties/ — that is where the invariants live, and a property
    nothing checks is a wish. Elsewhere it is a warning on `constraint` files
    that shout a binding rule and name nothing, which `--strict` turns into a
    release-gating error.
    """
    # By declared type OR by name: an INDEX.md is a routing table in this
    # methodology, and a pre-2026 KB that predates the `type:` key would
    # otherwise have every ID its index lists read as an unenforced claim.
    if fm.get("type") == "index" or os.path.basename(rel) == "INDEX.md":
        return                      # routing tables list claims, they do not make them
    # Any directory named properties/, not just the KB root's: a large KB
    # nests sub-KBs (tezqed carries webapp/properties/), and a rule that only
    # looked at the top level let every nested claim through unchecked.
    if "properties" in rel.split(os.sep)[:-1]:
        for claim, line, values, hint, region in find_claims(body):
            if not values:
                errors.append((rel, f"E-unenforced: {claim} (line {line}) declares no "
                                    "`Enforced-by:` — name the test, script, or hook "
                                    "that holds it, or `none: <reason>`" + (hint or "")))
            for value in values:
                problem = check_channel(value, kb)
                if problem:
                    errors.append((rel, f"{problem[0]}: {claim}: {problem[1]}"))
            if any(v.lower().startswith("proof") for v in values) and \
                    not any(TRUST_RE.match(l) for l in region):
                warnings.append((rel, f"W-trust: {claim} is held by a proof but never "
                                      "says what the proof leaves out — name the "
                                      "statement, the boundary and the kernel "
                                      "(`Trusted:` / `Not covered:`)"))
    elif fm.get("type") == "constraint" and BINDING_RE.search(body) \
            and not declared_channels(body.splitlines()):
        warnings.append((rel, "W-unenforced: states a binding rule (MUST/NEVER) but "
                              "names no `Enforced-by:` channel — make it mechanical "
                              "where you can, else `none: <reason>`"))


def main():
    ap = argparse.ArgumentParser(
        description="Mechanical validation for agent-optimized knowledge bases.")
    ap.add_argument("kb_dir", nargs="?", default="kb")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--required-keys", default=",".join(DEFAULT_REQUIRED))
    args = ap.parse_args()
    required = [k.strip() for k in args.required_keys.split(",") if k.strip()]

    kb = os.path.abspath(args.kb_dir)
    if not os.path.isdir(kb):
        print(f"kb-lint: no such directory: {kb}", file=sys.stderr)
        return 2

    errors, warnings = [], []
    files = {}       # relpath -> (frontmatter, text)
    ids = {}         # id -> relpath
    linked_to = set()

    for root, dirs, names in os.walk(kb):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in sorted(names):
            if name.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, name), kb)
                with open(os.path.join(kb, rel), encoding="utf-8") as f:
                    files[rel] = f.read()

    today = datetime.date.today().isoformat()

    # -- glossary terms are collected up front so the main pass can flag
    #    re-definitions (define once: terms live in the glossary only).
    glossary_terms = {}
    for rel, text in files.items():
        fm, _ = parse_frontmatter(text)
        if fm and fm.get("type") == "glossary":
            for m in TERM_DEF_RE.finditer(strip_fences(text)):
                glossary_terms[m.group(1).strip().lower()] = rel

    for rel, text in sorted(files.items()):
        # Exempt files (reports, question rounds) are historical artifacts:
        # their links legitimately rot as the KB evolves, so skip them fully.
        if is_exempt(rel):
            continue

        for target, bare in extract_links(text):
            cands = [os.path.normpath(os.path.join(os.path.dirname(rel), target)),
                     os.path.normpath(target)]
            hit = next((c for c in cands if c in files), None)
            if hit:
                linked_to.add(hit)
            elif bare:
                warnings.append((rel, f"W-bare-link: `{target}` resolves nowhere"))
            else:
                # The target escapes the KB: resolve on the filesystem,
                # relative to the file's own directory and to the repo root.
                fs_cands = [os.path.join(kb, os.path.dirname(rel), target),
                            os.path.join(kb, "..", target)]
                if not any(os.path.exists(os.path.normpath(c)) for c in fs_cands):
                    errors.append((rel, f"E-link: `{target}` does not exist"))

        fm, err = parse_frontmatter(text)
        if fm is None:
            errors.append((rel, f"E-frontmatter: {err}"))
            fm = {}
        for key in required:
            if key not in fm:
                errors.append((rel, f"E-key: missing `{key}` in frontmatter"))
        if "type" in fm and "type" in required and fm["type"] not in TYPE_SET:
            errors.append((rel, f"E-type: `{fm['type']}` not in {sorted(TYPE_SET)}"))
        if "id" in fm:
            if fm["id"] in ids:
                errors.append((rel, f"E-dup-id: `{fm['id']}` also declared "
                                    f"in {ids[fm['id']]}"))
            else:
                ids[fm["id"]] = rel

        lu = fm.get("last-updated", "")
        if "last-updated" in fm and "last-updated" in required:
            try:
                datetime.date.fromisoformat(lu)
            except ValueError:
                errors.append((rel, f"E-date: last-updated `{lu}` is not YYYY-MM-DD"))
                lu = ""

        body = strip_fences(text)
        if fm.get("type") == "procedure":
            for m in RATIONALE_HEADER_RE.finditer(body):
                warnings.append((rel, f"W-register: `{m.group(0).strip()}` in a "
                                      "procedure file — move the why to an ADR "
                                      "and link it"))
        if fm.get("type") != "glossary":
            for m in TERM_DEF_RE.finditer(body):
                term = m.group(1).strip()
                if term.lower() in glossary_terms:
                    warnings.append((rel, f"W-redefine: `{term}` is defined in "
                                          f"{glossary_terms[term.lower()]} — "
                                          "link it instead of re-defining"))

        check_enforcement(rel, body, fm, kb, errors, warnings)

        max_lines = int(fm.get("lint-max-lines", DEFAULT_MAX_LINES))
        n = text.count("\n") + 1
        if n > max_lines:
            errors.append((rel, f"E-length: {n} lines > {max_lines} "
                                "(split the file, or document the exception "
                                "with `lint-max-lines: N`)"))

        if not args.no_git and lu:
            commit, dirty = git_dates(kb, rel)
            if commit and commit > lu:
                warnings.append((rel, f"W-stale: last commit {commit} is newer "
                                      f"than last-updated {lu}"))
            if dirty and lu != today:
                warnings.append((rel, f"W-dirty: uncommitted changes but "
                                      f"last-updated is {lu}, not {today}"))

    # -- id references resolve only after every id is known.
    for rel, text in sorted(files.items()):
        if is_exempt(rel):
            continue
        fm, _ = parse_frontmatter(text)
        if not fm:
            continue
        for key in ID_REF_KEYS:
            refs = fm.get(key, [])
            if isinstance(refs, str):
                refs = [refs] if refs else []
            for ref in refs:
                if ref and ref not in ids:
                    errors.append((rel, f"E-id-ref: {key} names unknown id `{ref}`"))

    # -- every directory with 2+ md files needs a routing table.
    for root, dirs, names in os.walk(kb):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        rel = os.path.relpath(root, kb)
        if rel != "." and is_exempt(os.path.join(rel, "x.md")):
            continue
        mds = [n for n in names if n.endswith(".md")]
        if len(mds) >= 2 and "INDEX.md" not in mds:
            errors.append((rel if rel != "." else "kb/",
                           "E-index: directory holds 2+ md files but no INDEX.md"))

    # -- orphans: unreachable files defeat the routing-table design.
    for rel in sorted(files):
        if rel == "INDEX.md" or is_exempt(rel):
            continue
        if rel not in linked_to:
            warnings.append((rel, "W-orphan: no other KB file links here"))

    for rel, msg in errors:
        print(f"ERROR {rel}: {msg}")
    for rel, msg in warnings:
        print(f"WARN  {rel}: {msg}")
    print(f"kb-lint: {len(files)} files, {len(errors)} errors, "
          f"{len(warnings)} warnings")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
