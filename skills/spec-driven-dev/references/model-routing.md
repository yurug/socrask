# Model routing rules

The tier table lives in SKILL.md. These rules apply it.

1. Phases 0–3 run in the main session — run the skill itself on the judgment tier.
2. Select a supported execution model explicitly when the host exposes that choice;
   `sonnet` is the Claude example, not a portable model name. Judgment tasks inherit
   the session model. If routing is unavailable, state that once and use the host default.
3. **Establish a capable reference before optimizing cost.** Use judgment capability
   for unfamiliar integration, acceptance design and consequential repairs, even with
   a written spec. A weaker model's failure does not prove the spec is wrong. Execution
   agents get at most two unsuccessful iterations before a structured handoff; repeated
   failures require a changed hypothesis. Preserve the shared seven-iteration ceiling.
4. **Test KB navigation with the agents that consume it.** Keep that diagnostic
   separate from product acceptance. For product agents, record the effective model
   of every decision-making helper, not just the model selected in the chat UI.
5. Machine checks (kb-lint, type checker, linter, tests) cost zero model tokens — run
   them before every model-based pass, at any tier.
