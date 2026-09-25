# Inbrief command-line reference

Inbrief opens a grounded onboarding session for an engineer. The coding agent
builds a question map from repository evidence; the engineer alone records
mastery in the browser.

Inbrief is not a standalone npm package. Install it from the public toolsuite
into the active Node/npm environment:

```sh
git clone https://github.com/yurug/engineer-engineering-tools.git \
  "$HOME/.local/share/engineer-engineering-tools"
"$HOME/.local/share/engineer-engineering-tools/install.sh" inbrief
```

If that checkout already exists, do not clone over it; inspect it and update it
normally. The installer builds the workspace, links `@inbrief/cli` into the
active `npm prefix -g`, and installs the Inbrief skill. Then invoke commands as
`inbrief …` or by the absolute path printed by the installer.

| Command | Does |
|---|---|
| `inbrief serve [--repo DIR] [--port N] [--open]` | Starts a local session and prints its URL, tokens, port, session id, and PID. |
| `inbrief act FILE.json` / `inbrief act -` | Posts an agent-authored node, agenda, answer, concession, finding, or close record. |
| `inbrief events [--since N] [--follow] [--timeout SECS] [--actor human]` | Reads human mastery changes and questions; timed follow exits on its first matching event. |
| `inbrief status` | Reports whether the server is running and the current coverage counts. |
| `inbrief propose [--out DIR]` | Prints durable material learned by the session, or writes proposals to an explicitly chosen scratch directory. |
| `inbrief stop` | Stops the server without claiming that the onboarding session completed. |

The server binds only to `127.0.0.1`. Runtime discovery and credentials live
under `.inbrief/`; the nested `.gitignore` excludes them.

## Contents

- [Payloads accepted by `act`](#payloads-accepted-by-act)
- [Safe write-back](#safe-write-back)
- [Checkpoint ownership and completion](#checkpoint-ownership-and-completion)

## Payloads accepted by `act`

Every payload carries a `kind`. Citation paths are repository-relative and line
numbers are one-based and inclusive. Omit revisions and hashes: the server mints
and validates them.

```json
{
  "kind": "node",
  "node": {
    "id": "append-only-recovery",
    "mode": "explanation",
    "question": "How does restart recovery work?",
    "answer": "The log is replayed in order; a torn final record is ignored.",
    "citations": [{ "kind": "code", "path": "src/log.ts", "startLine": 20, "endLine": 45 }],
    "requires": [],
    "introduces": [],
    "uses": [],
    "visual": {
      "schemaVersion": "0.4.0",
      "kind": "diagram",
      "trust": "grounded",
      "title": "Recovery order",
      "meaning": "flow",
      "nodes": [
        {
          "id": "log",
          "label": "Saved records"
        },
        {
          "id": "state",
          "label": "Restored state"
        }
      ],
      "edges": [
        {
          "from": "log",
          "to": "state",
          "label": "replay in order"
        }
      ]
    },
    "lifetime": "durable"
  }
}
```

Node questions are limited to 12 words and answers to 60. `mode` is `tutorial`
or `explanation`; `lifetime` is `durable` or `snapshot` and defaults to the
safer `snapshot`. Every node needs at least one resolving citation.

`requires`, `introduces`, `uses`, and `visual` are required. Explicit empty
vocabulary arrays mean no technical term is being introduced or assumed, not
permission to hide jargon. Each `introduces` term must appear in the answer and
must not appear in the question. Every `uses` term must appear in the question or
answer and be introduced by a transitive prerequisite. Post prerequisites first.

`visual` is a validated `@brief/primitives` spec, not SVG or HTML. The installed
renderer accepts diagram, filmstrip, rail, lanes, or layers; the example uses its
0.4.0 diagram schema. Validate with the installed renderer when adapting it.
Missing metadata yields `vocabulary-metadata-missing`; a missing visual yields
`visual-missing`. Check `admitted: true` and empty `refusals`, not just citation
validity, before placing a node in an agenda. HTTP 422/CLI exit 1 means refused.
The citation path and lines above are illustrative: replace them with actual
repository evidence. Runtime schema changes require rechecking one real node
before posting the rest of a map.

Other accepted shapes:

```json
{"kind":"agenda","agenda":["append-only-recovery"],"intent":"Understand recovery before changing the scheduler"}
{"kind":"answer","question":12,"by":"reply","text":"The malformed suffix is reported and skipped."}
{"kind":"concession","node":"append-only-recovery"}
{"kind":"finding","text":"Recovery accepts an invalid checksum.","citation":{"kind":"code","path":"src/log.ts","startLine":31,"endLine":34}}
{"kind":"close"}
```

`answer.by` is `node`, `reply`, or `gap`. A concession is valid only after the
engineer contested that node. Mastery and engineer questions are intentionally
absent from the CLI because only the browser carries the human credential.

## Safe write-back

`inbrief propose` writes nothing by default. With `--out`, it writes only into
the named directory. Review those files and move selected durable material into
the project as an ordinary commit; a session must never silently author project
documentation.

## Checkpoint ownership and completion

The coordinator starts one session for the concepts needed by the next decision,
not one session per worker. Mark the alignment record `pending` as soon as it is
opened. After sharing the URL, consume `inbrief events --actor human --since N
--follow --timeout 20`; react to each envelope before advancing the cursor.
A dedicated listener may relay events, but does not answer for the engineer.

The installed CLI permits agent `close` actions. Therefore `closed: true` alone
cannot demonstrate a human-closed checkpoint. Inspect the human event evidence
and the actual coverage/unknowns before recording `human-complete`; cite session
and event references, never tokens. A human question, an agent reply, or a browser
visit alone is not proof of coverage. If human completion is absent, retain
`pending` or cite explicit fallback authorization as `degraded-authorized`.
Installation and personal concept profiles are optional. See `docs/alignment.md`.
