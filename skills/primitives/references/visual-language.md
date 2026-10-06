# Visual language

This reference separates **what the reader must perceive** from the renderer
entry used to draw it. Treat `rail`, `lanes`, `layers`, `diagram`, `filmstrip`,
`chart`, `matrix`, and `claim` as implementation entries, not as the complete
visual vocabulary.

## Contents

- [Start with perception](#start-with-perception)
- [Choose a composition](#choose-a-composition)
- [Build from primitives](#build-from-primitives)
- [Use the token roles](#use-the-token-roles)
- [Apply composition recipes](#apply-composition-recipes)
- [Check the result](#check-the-result)

## Start with perception

Before writing a spec, complete this sentence:

> The reader must see **___** before reading the details.

Use one concrete relationship: order, ownership, boundary, difference,
magnitude, or topology. If the blank contains only a topic such as
"authentication", the visual has no perceptual job yet.

Set three constraints:

1. **Primary perception** — the one relationship visible at a glance.
2. **Reading order** — left-to-right, top-to-bottom, center-out, or scan-anywhere.
3. **Density** — glance (under 10 seconds), study (under one minute), or reference.

## Choose a composition

| Primary perception | Composition | Reading order | Renderer today |
|---|---|---|---|
| order, duration, or change | narrative rail | left-to-right | rail |
| ownership and hand-offs | swimlanes | left-to-right within top-to-bottom lanes | lanes |
| boundaries and responsibility | layered stack | top-to-bottom | layers |
| alternatives against shared criteria | comparison matrix | rows then columns | matrix |
| magnitude, health, or distribution | scorecard / quantitative chart | scan-anywhere or axis order | chart / claim |
| adjacency, reachability, cycles, or dependency | relationship map | path-following | diagram |

`gap` means the current renderer cannot preserve that composition. Do not force
the content into a diagram. Prefer prose or a table, or follow the skill's
visible **unvalidated visual** route and log the missing composition.

### Graph veto

Use a relationship map only when removing the connectors would destroy the
answer. Nouns that can be connected do not by themselves justify a graph.

Do not use a graph to show:

- a sequence with one dominant path — use a rail;
- actors doing work over time — use lanes;
- nested responsibilities — use layers;
- options and criteria — use a matrix;
- a handful of health measures — use a scorecard.

## Build from primitives

Compose with a small vocabulary. A composition should rarely need every item.

| Family | Primitive | Job |
|---|---|---|
| content | label | name a role, phase, or measure at the point of use |
| content | title | state the visual's conclusion or question |
| content | caption | say what changed or how to read the view |
| content | metric | pair one value with its unit and interpretation |
| grouping | frame | establish trust and the outer evidence boundary |
| grouping | surface | group related content without implying interaction |
| grouping | card | make one comparable unit repeatable |
| grouping | lane | assign activity to an actor or system |
| relation | rail | encode order without advertising arbitrary topology |
| relation | connector | encode a named dependency or hand-off |
| relation | scale | make magnitude spatially comparable |
| annotation | badge | carry a short state, never a second title |
| annotation | callout | explain one exceptional point next to it |
| annotation | trust mark | distinguish grounded from conjectural claims |

Prefer layout primitives (`stack`, `cluster`, `grid`) over coordinates. They
create rhythm and survive different label lengths and viewport widths.

## Use the token roles

The package's exported `TOKENS` object remains the implementation source of
truth. Evolve it by semantic role rather than by component-specific values.
The specimen in `../assets/visual-language.html` prototypes these additions.

### Color

- `canvas` — the host page; never encode data with it.
- `surface` and `surface-subtle` — grouping hierarchy.
- `ink`, `ink-muted`, `border` — reading hierarchy.
- `accent` and `accent-soft` — current focus or recommended path.
- `signal` — attention or hand-off, not generic decoration.
- `success` — verified or completed state.
- `conjecture` — reserved for trust chrome.

Never assign a new color merely to make adjacent cards look different. One
semantic role keeps the same color across every composition.

### Type and space

- Use a display face only for page and composition titles; keep labels neutral.
- Use at most three text sizes inside one composition.
- Use the 4-based spacing scale: 4, 8, 12, 16, 24, 32, 48, 64.
- Increase whitespace before adding borders. Add a surface before adding a box.
- Keep body lines near 55–75 characters where prose appears.

### Shape and stroke

- Use corner radius to identify a component family, not status.
- Keep structural rules quiet; make the encoded path heavier than furniture.
- Use dashed strokes only for conjecture or a genuinely discontinuous relation.
- Avoid shadows and gradients unless a future evidence-backed role requires them.
- Keep identity motifs in page chrome, outside the evidence frame. Inside the
  frame, every visible element must carry hierarchy, grouping, or data.

## Apply composition recipes

### Narrative rail

Use one rail, 3–7 stops, one sentence per stop, and a single highlighted
transition. Put time or phase labels above the rail and outcomes below it.

### Swimlanes

Use 2–5 lanes with persistent actor labels. Align hand-offs vertically. Keep
activity inside its owner's lane; use connectors only when ownership changes.

### Layered stack

Use 3–5 layers ordered by dependency or abstraction. Give each layer one job.
Show crossing concerns as a side rail rather than duplicating them in layers.

### Comparison matrix

Keep criteria stable across columns. State the recommendation in the title,
then use emphasis to make its evidence scannable. Never use unexplained scores.

### Scorecard

Use 3–6 measures with shared directionality. Pair every value with a baseline,
target, or verbal interpretation. A number without a comparison is decoration.

### Relationship map

Use it for non-linear topology. Limit the first view to one focal node, one
relation vocabulary, and the paths needed for the stated question. If every
node has equal visual weight, the map has no reading order.

## Check the result

- Can a reader name the primary relationship after five seconds?
- Is there exactly one obvious entry point?
- Does position carry more meaning than decoration?
- Are labels attached to what they label?
- Is every color tied to a stable semantic role?
- Could one border, connector, or badge be removed without losing information?
- Is trust visible at the evidence boundary?
- Would a table or two sentences communicate the point faster?

The reference specimen intentionally renders all six compositions around one
case study. Compare them for fitness; do not treat the gallery as six skins for
the same data.
