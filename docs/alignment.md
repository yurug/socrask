# Human checkpoints

One coordinator owns Inbrief, Forebrief, and Backbrief for a bounded change.
Workers return findings and validation; they do not create competing human sessions.
Forebrief records decisions. Inbrief explains concepts needed before a decision.
Backbrief explains the final aggregate diff, including worker changes, KB, and docs.

Use Inbrief for Full work, new subsystems, or unfamiliar load-bearing concepts.
A Slice on familiar ground may omit it with a specific reason. Every non-Direct
change needs Backbrief. Direct changes record why neither session is necessary and
still receive a concise result summary. Grow the tier when the actual scope grows.

## Record and gate

The coordinator supplies `agent-work.py claim --alignment FILE`; workers claim
with `--role worker --coordinator TASK`. Claim checks the coordinator's start
record. Technical handoff can finish while Backbrief is pending. Integration
closure checks the final record against the actual base and integrated head;
worker closure follows successful coordinator closure. An abandoned task is
explicitly abandoned, never silently counted as aligned.

Keep one version-1 JSON record per coordinator change, accessible to its reviewers:

```json
{
  "version": 1,
  "work_id": "scheduler-recovery",
  "tier": "slice",
  "base": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "checkpoints": {
    "inbrief": {
      "status": "not-required",
      "reason": "Existing recovery model is unchanged; no unfamiliar decision"
    },
    "backbrief": {
      "status": "required",
      "reason": "Review recovery behavior and its validation after implementation"
    }
  }
}
```

At finish add `head` with the full reviewed commit hash. Run:

```sh
python3 tools/alignment-check.py path/to/alignment.json --stage start --base "$BASE"
python3 tools/alignment-check.py path/to/alignment.json --stage finish --base "$BASE" --head "$HEAD"
```

| Status | Meaning |
|---|---|
| `required` | Due, not yet opened |
| `pending` | Started; required human evidence still missing |
| `human-complete` | Actual substantive human checkpoint evidence recorded |
| `degraded-authorized` | Human explicitly authorized the limited fallback or skip |
| `not-required` | The tier/context rule permits omission; concrete reason recorded |

Every entry needs `reason`. `human-complete` additionally requires
`"evidence":{"kind":"human-event","ref":"backbrief:SESSION:event:SEQ"}`.
`degraded-authorized` requires
`"evidence":{"kind":"human-authorization","ref":"conversation:turn:ID"}`.
Use genuine stable references to human actions or statements, not invented IDs.
Do not include tokens, browser credentials, event transcripts, or personal profiles.
A reference can remain private to the owner; report that limitation to reviewers.

Start refuses unresolved Inbrief; it allows future Backbrief. Finish refuses any
unresolved checkpoint, invalid tier exemption, missing evidence reference, or
mismatched base/head. A changed diff needs refreshed Backbrief evidence. The checker
checks declarations and diff bounds; it cannot authenticate a reference or prove
comprehension. A dishonest author can forge JSON, so this is an auditable workflow
gate, not a human identity or knowledge verifier.

## Operate the sessions

Resolve the installed binary using
`skills/spec-driven-dev/resolve-engineering-tool.sh inbrief` (or `backbrief`).
Follow that skill's `references/inbrief-cli.md` or `references/backbrief-cli.md`.
Post grounded explanations, share the browser URL, then consume human events with
a bounded `events --actor human --since N --follow --timeout 20` loop. React before
advancing the saved cursor. One coordinator receives events; a worker assigned as
a listener only relays them. Never copy human credentials or impersonate the user.

Inbrief's agent can post `close`; that is not human closure evidence. Backbrief's
`humanSeen` means presence, not comprehension. Neither stopping a server nor
sending a URL settles a checkpoint. If the tool is unavailable or the human wants
to continue without it, give a short explanation of the limitation and record
explicit authorization for the fallback. Tool absence alone is not authorization.
While pending, continue independent work and report the checkpoint as pending;
do not claim the whole workflow complete.

## Laconic is communication discipline

Lead with the outcome or decision, the necessary context, and the next action.
For a decision give options, recommendation, consequences, and material uncertainty.
For a result explain what changed, why, validation, and remaining limits. Offer
supporting detail when useful; brevity must not conceal a risk or open question.

Use conversation context without building an unsolicited personal profile. A
persistent engineer model requires owner opt-in and remains private. Asking a
question is not evidence of ignorance: answer with a relevant source and improve
the explanation. Never infer understanding from silence or agent-written answers.
