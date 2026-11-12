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
6. **Context is a budget.** A model reasons worse as its context fills, well before
   the window is full. It also gives less weight to what came early. Write each
   phase's results to files as you go (`kb/`, `kb/reports/`, `SESSION_STATE.md`), so
   that the next phase, or a fresh session, can start from the files alone. When a
   long phase has filled much of the context, save to a file, then compact or start
   fresh before the next gate. Give a context-heavy survey to a subagent, which
   returns only its conclusion.
7. **An operation that follows a rule goes to a tool, not to a model.** A mechanical
   change, a derived file or a repeated query is a script: the model writes it once,
   and the reviewer reads its rule instead of each site
   ([deterministic tools](deterministic-tools.md)). The execution tier writes the tool;
   the judgment tier writes it when it touches a kernel.
