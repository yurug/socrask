---
id: architecture-overview
type: concept
summary: The components of the system, what each hides, the state it owns and what it depends on.
domain: architecture
last-updated: YYYY-MM-DD
related: [architecture-drivers, critical-core]
---

# Architecture overview

## One-liner
[The system's shape in one sentence.]

## Components

Checked by `tools/arch-check.py`: paths are backticked, dependencies name other components or `-`.

| Component | Paths | Depends on | Hides | Owns state | Authority |
|---|---|---|---|---|---|
| [name] | `[src/dir]` | [other components, or -] | [the decision likely to change] | [state, or -] | [capabilities] |

## Dependency rules
[Direction of dependencies, layers, what must never depend on what.]
