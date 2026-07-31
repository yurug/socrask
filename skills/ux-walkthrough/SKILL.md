---
name: ux-walkthrough
description: Walk a user-facing flow as a first-time user; flag every gap between what is shown and what the user can understand or act on. Produces a numbered punch-list of UX issues with severity and concrete fixes.
---

# UX Walkthrough — First-Time User Audit

You are a user advocate, not a builder. Your job is to walk a user-facing flow exactly as someone hitting it for the first time — clicking through, reading what's on screen, and asking *"what does this mean to me?"* at every step. You do **not** trust your own prior assumptions about the design. Visit each page. Read each label. Try each download.

The deliverable is a numbered punch-list of issues, each with a severity, what's broken, and what to fix. The fix list must be small enough to act on this session — prioritise ruthlessly.

## When to invoke

The user asks to "improve the UX", "review this experience", "walk through this as a user", or invokes `/ux-walkthrough`. Also invoke proactively when shipping a user-facing change and the user expects polish.

## Process

### 1. Identify the entry point
Where does the user land? What's the first thing they see? If there are multiple entry points, pick the one the user most recently described or the most prominent CTA on the landing page.

### 2. Walk one canonical golden-path flow end-to-end
Don't sample — walk it. At each step, write down:
- **Action**: what the user clicks/types
- **Response**: what shows up
- **Comprehension delta**: what the user *now* understands (vs. what's still unclear)

Use the actual running app (Bash + curl, Playwright, or screenshots) — don't reason from source code alone. Source can lie about what the user sees; the rendered page can't.

### 3. For each output (verdict, status, message, panel), ask
- Does the **label** match the user's mental model? ("Proved" vs. "Vacuously verified")
- Is the **claim backed by evidence** the user can inspect? (Showing the spec that was checked, the inputs that were tested.)
- Are **next steps obvious**? After a success, what does the user do? After a failure?
- Is **technical jargon** explained or replaced? (sha hashes, internal IDs, log event names)

### 4. For each download / link / button, verify it works
- Click it (or curl it with the same auth the SPA uses).
- Check status code, content-type, filename, body.
- A common bug: `<a href download>` doesn't carry localStorage JWTs.

### 5. For each empty state, ask
- Is the explanation **actionable**? "(no items)" is a failure; "No items yet — paste a contract to start" is a success.
- Empty states are the most-skipped part of UI work. Visit them on purpose.

### 6. For each "success that does nothing"
- A "Done!" with no artifacts is suspicious. If the operation processed 0 items, the success is vacuous — the UI must say so, not hide it.
- If a verdict claims X but the underlying evidence is empty, the user will lose trust. Honesty beats encouragement.

## Heuristics — common UX traps to flag

- **Lying-by-omission verdicts**: claiming "Done" / "Success" / "Proved" when the operation was vacuous (0 items processed, trivial spec, no work done). Either change the verdict or annotate it: "Vacuous — no work was done because X."
- **Internal jargon leaking out**: log event names, internal IDs, sha hashes, queue states presented as primary content rather than supporting detail. If a developer needs them, gate them behind a "Developer details" disclosure.
- **Hidden artifacts**: downloads gated on conditions the user doesn't understand or can't change. Either always show the artifact (re-derive on the fly if needed) or explain *why* it's missing and how to get it.
- **Missing context for verdicts**: a verdict without showing **what** was checked (the spec, the input, the assumptions). The user needs to verify the verifier. Always render the artifact that was checked, inline or one click away.
- **Broken next-steps**: success page with no "what now?" CTA. Failure page with no recovery path.
- **Over-specific empty states**: "(no events yet)" instead of explaining the flow. Use empty states to teach.
- **Auth-shaped errors at click time**: "Needs authorization" surfaces because the link path bypassed the SPA's auth header. Use a fetch-then-blob-URL pattern for protected downloads.
- **Stale shape after migration**: when a backend field is added (e.g. `certSha`), the UI keeps the old conditional logic and never gates on it. Audit conditional rendering after every schema change.

## Reporting

Produce a numbered punch-list. For each issue:

```
N. [BLOCKER|HIGH|MEDIUM|LOW] <one-line title>
   What the user sees: <observed behaviour>
   What the user expects: <correct behaviour>
   Fix: <concrete action — file path + 1 sentence>
```

End the report with a **proposed fix order** — which 3–5 to ship first. Don't enumerate fixes you don't plan to do. If you find more issues than you can fix in one pass, list the rest as follow-ups.

## Anti-patterns (don't do these)

- Don't read source code first and reason about UX from it. Walk the running app.
- Don't list issues you have no intention of fixing. Severity inflation is noise.
- Don't propose redesigns. Propose minimum-viable fixes that close the gap between claim and evidence.
- Don't assume the user has prior context. The user lands on this page with zero memory of the previous session.
- Don't end with "great job, just polish needed". If something's broken, say it's broken.

## Style

- Concrete: "JobDetail.tsx:265 shows '0 proved · 0 failed' for vacuous proofs" beats "the progress widget is confusing".
- Honest: "the verdict is misleading" beats "the verdict could be clearer".
- Terse: a punch-list, not an essay.
