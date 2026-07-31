---
name: primitives
description: "Render explanatory visuals from validated JSON specs instead of hand-rolling HTML or SVG — diagrams, stepped sequences (filmstrips), charts, trade-off matrices, and assertion-evidence cards, with evidence-backed defaults baked in. Use whenever you are about to draw something for a human: a diagram in a report, a comparison in an artifact, a mechanism walkthrough, a chart of measurements. Also use before choosing to animate anything."
---

# Communication primitives

You emit a JSON spec; the library validates it and renders it. You never write
the markup. This exists so the work of making a visual communicate well is
paid once, in the renderer, instead of re-derived every time you draw.

## Is the library available?

`ls node_modules/@backbrief/primitives` (or the sibling checkout at
`../backbrief/packages/primitives`). If absent: write plain prose and a table,
mark nothing as a visual, and stop reading this file. Never half-apply this.

## The five primitives, and when each one is right

| You are showing | Use | Entry |
|---|---|---|
| A structure or relationship (flow, state machine, dependencies, causality) | diagram | `@backbrief/primitives/diagram` |
| How a mechanism unfolds, step by step | **filmstrip** | `.../filmstrip` |
| Quantities, trends, distributions, comparisons | chart | `.../chart` |
| Options against criteria | matrix | `.../matrix` |
| One claim with one piece of evidence | claim | `.../claim` |

Specs are documented in the host repo's KB when it has one (backbrief:
`kb/primitives/primitive-specs`). Read that before writing your first spec of
a kind; the schemas reject unknown fields, and the error names the field.

## The rules that are not yours to relitigate

**Static first.** Animation's measured advantage over static graphics is
small (g ≈ 0.226) and vanishes when the reader controls the pacing. The
filmstrip — stills the reader advances — is how you explain a mechanism.
Animate only when the motion IS the content, and then only from a
hand-written parameterized template. **Never emit animation code.**

**A filmstrip is one graph plus deltas, not N graphs.** Declare every node any
step shows in `base`, then reveal, conceal, emphasize, dim, or relabel per
step. You cannot add or remove structure between steps — that is what keeps
unchanged elements from moving, which is the whole reason the reader can read
the delta.

**Every step carries a one-sentence caption saying what changed.** Not a
title. What changed.

**A claim's headline asserts something.** "Auth tokens expire in 15 minutes"
is a headline. "Authentication" is a topic phrase and the schema rejects it.

**Labels go on the thing they label.** Charts get inline series labels, never
a legend; diagram edge labels ride the edge. The strongest effects in the
evidence base are contiguity and subtraction, in that order.

**Nothing decorative.** No gradients, shadows, background fills, 3D, or
decorative color. One accent plus neutrals. If an element carries no
information, delete it.

**Charts are server/build-time only.** Import the chart entry for its schema
and compiler freely, but calling the renderer pulls ~767 KB — do it in Node or
at build time and embed the resulting SVG. Never call it in a browser bundle.

## Trust

Every spec declares `trust: "grounded" | "conjecture"`, and the renderer
frames the visual accordingly — solid, or dashed with a tag. A visual that
mixes a validated claim with a prediction is **conjecture**: the frame takes
the weakest claim in it. Do not argue with this by splitting hairs; split the
visual instead if the distinction matters.

## When prose really is better

Some content has no structure, sequence, comparison, or quantity in it, and a
visual would be decoration. Say so on the artifact, in one line, and the gate
stops asking:

    > No visual: a single score and three named defects — a two-bar chart of a
    > number is decoration.

Either form works: a `No visual: <reason>` line, or `<!-- no-visual: <reason> -->`.
The reason has to be a reason; the phrase alone does not count.

## When a spec cannot express what you need

This will happen. The rule (backbrief `kb/architecture/decisions/ADR-009`):

1. Render it however you must — outside the library.
2. **Mark it visibly as an unvalidated visual.** An unmarked hand-rolled
   visual is indistinguishable from a validated one, which is the failure this
   whole arrangement exists to prevent.
3. Log what was missing: a `forebrief act` feedback record if the repo is
   forebrief-enabled, otherwise a line in your report. That record is what
   feeds schema evolution — silence means the gap never gets closed.

There is no raw-markup field in any spec, and asking for one is asking to
delete the guarantee.

## Version skew

Specs carry `schemaVersion`. If a renderer reports skew instead of a visual,
its copy is stale — run the refresh script it names (`tools/refresh-primitives.sh`
in backbrief) rather than editing the spec to match an old schema.

## Self-check before you ship a visual

- Would a static filmstrip do what I was about to animate? (Almost always: yes.)
- Does every claim in this visual actually hold, or is the frame lying?
- Is there a legend I could have made an inline label?
- Did I hand-roll something and forget to mark it?
