#!/usr/bin/env python3
"""Visual honesty and diversity gate for generated artifacts.

The checks are deliberately asymmetric. An UNMARKED hand-rolled visual is a
hard error (that is a mechanical fact about the file, and it is the failure
that looks like success). A MISSING visual and a DIAGRAM-ONLY visual corpus are
warnings: relevance and composition are judgments, so the gate asks rather
than pretending it can decide.

    skills/primitives/visual-check.py [DIR ...]

DIR defaults to this repo's own artifact directories. No machine-specific
defaults — this ships in a public kit.

Exit 1 on any error, 0 otherwise (warnings never fail).

What counts as a hand-rolled visual: inline <svg>, a <canvas>, or a mermaid
block. Those are drawings. A <table> is NOT — tables are legitimate prose
furniture and flagging them produced nothing but noise in trials.

What counts as validated: the file references a primitives spec kind or a
primitives entry point, i.e. the visual came from a renderer that enforces the
design defaults rather than from improvisation.

What counts as the honest marker: the phrase "unvalidated visual", case
insensitive. That is the exact wording the primitives skill instructs, so the
gate and the instruction cannot drift apart.
"""

import os
import re
import subprocess
import sys

DRAWING_RE = re.compile(r"<svg[\s>]|<canvas[\s>]|```mermaid|class=\"mermaid\"", re.I)
SPEC_RE = re.compile(
    # data-primitive is the renderers' own provenance stamp; the other two forms
    # catch a spec embedded as JSON or an import of an entry point.
    r'data-primitive="(diagram|filmstrip|chart|matrix|claim|rail|lanes|layers)"'
    r"|primitives/(diagram|filmstrip|chart|matrix|claim|rail|lanes|layers)"
    r'|"kind"\s*:\s*"(diagram|filmstrip|chart|matrix|claim|rail|lanes|layers)"',
)
MARKER_RE = re.compile(r"unvalidated visual", re.I)

# A stated reason closes the question. The decided policy is "ask once, and a
# one-line reason is always an acceptable answer" — a gate that keeps warning
# after the answer was given implements only the asking half, and turns into
# permanent noise the author learns to ignore. Canonical forms, both requiring
# an actual reason after the colon (>= 20 chars, so the phrase alone is not
# enough): a blockquote line "> No visual: ..." / "No visual here on purpose:
# ..." or an HTML comment "<!-- no-visual: ... -->".
NO_VISUAL_REASON_RE = re.compile(
    r"(?:no visual(?:\s+here)?(?:\s+on purpose)?\s*[:—-]|<!--\s*no-visual\s*:)\s*(.{20,})",
    re.I,
)

# Artifact genres whose content nearly always has a diagrammable shape. Missing
# a visual here is worth saying out loud -- as a warning, never a failure.
GENRE_HINTS = {
    "premortem": "failure modes are causal chains",
    "audit": "findings have severity and structure",
    "research": "effect sizes and comparisons are chartable",
    "quiz": "score distributions and gaps are chartable",
}


def default_dirs():
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        root = os.getcwd()
    return [os.path.join(root, d) for d in ("kb/reports", "reports", "research", "methodology")]


def primitive_kinds(text):
    kinds = set()
    for match in SPEC_RE.finditer(text):
        kinds.update(group for group in match.groups() if group)
    return kinds


def check_file(path, errors, warnings):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return set()
    drawn = bool(DRAWING_RE.search(text))
    kinds = primitive_kinds(text)
    spec = bool(kinds)
    marked = bool(MARKER_RE.search(text))

    if drawn and not spec and not marked:
        errors.append(
            (path, "E-unmarked-visual: a hand-drawn visual with no primitives spec and no "
                   '"unvalidated visual" marker — indistinguishable from a validated render')
        )
    if not drawn and not spec:
        if NO_VISUAL_REASON_RE.search(text):
            return kinds  # asked and answered
        base = os.path.basename(path).lower()
        for genre, why in GENRE_HINTS.items():
            if genre in base:
                warnings.append((path, f"W-no-visual: a {genre} artifact with no visual ({why})"))
                break
    return kinds


def main():
    dirs = sys.argv[1:] or default_dirs()
    errors, warnings, scanned, visual_files = [], [], 0, []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for root, subdirs, names in os.walk(d):
            subdirs[:] = [s for s in subdirs if not s.startswith(".")]
            for name in sorted(names):
                if name.endswith((".html", ".md")):
                    scanned += 1
                    path = os.path.join(root, name)
                    kinds = check_file(path, errors, warnings)
                    if kinds:
                        visual_files.append((path, kinds))

    if len(visual_files) >= 3 and all(kinds == {"diagram"} for _, kinds in visual_files):
        warnings.append(
            (
                "visual corpus",
                "W-diagram-monoculture: every validated visual is a diagram; "
                "name the intended perception and consider a rail, lanes, layers, "
                "matrix, scorecard, prose, or table",
            )
        )

    for path, msg in errors:
        print(f"ERROR {path}: {msg}")
    for path, msg in warnings:
        print(f"WARN  {path}: {msg}")
    print(f"visual-check: {scanned} artifacts, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
