# Writing standard for human-facing artifacts

People read plans, reports, briefs, decision cards and changelogs without the
session that produced them. Many readers are not native English speakers. The
kit uses the writing rules of ASD-STE100, Simplified Technical English (STE).
STE is a controlled language from aerospace maintenance documentation.

We take its writing rules, not its dictionary. That dictionary is for
aerospace, so the project glossary (`kb/GLOSSARY.md`) is the approved-term list.

## Scope

The standard applies to files a person reads to understand or decide:
`kb/plan.md`, `kb/reports/`, forebrief cards, inbrief and backbrief text, and
the changelog. It does not apply to code, to KB prose that only agents read,
or to chat replies.

## Rules

1. One sentence, one idea. A sentence has 25 words or fewer. A step in a
   numbered procedure has 20 words or fewer.
2. Use the active voice. Say who does what: "the worker retries the job", not
   "the job is retried".
3. Write *must* for a rule and *can* for a possibility. Do not use *should*,
   *may* or *might*: state the fact or the rule.
4. One word, one meaning. Use the glossary term every time. A glossary entry
   can list rejected synonyms after `Not:`, for example
   `- **obligation**: a property ID a step must satisfy. Not: requirement.`
5. Start each procedure step with a verb in the imperative.
6. Put the result first, then the reason.

Rule 4 replaces STE's dictionary. A word with one meaning in the glossary does
not get a second meaning in a plan.

## Check

```sh
python3 tools/ste-check.py kb/plan.md kb/reports/*.md
printf '%s' "$CARD_TEXT" | python3 tools/ste-check.py -
```

Errors (long sentence, rejected glossary word) fail the build. Hedges and the
passive voice are warnings, because their detection is a heuristic.

The checks are structural. The kit uses no readability score: a score rewards
short words, not clear meaning. The script does not check that a sentence says
one thing, or that the reader can act on it. The reader's questions show that.
