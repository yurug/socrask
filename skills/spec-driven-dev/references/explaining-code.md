# Explaining code

## Contents

- [The standard](#the-standard)
- [Explanation moves](#explanation-moves)
- [What a comment must not do](#what-a-comment-must-not-do)
- [The explanation pass](#the-explanation-pass)
- [The cold read](#the-cold-read)
- [Measure it](#measure-it)
- [Reading list](#reading-list)
- [What is not checked](#what-is-not-checked)

## The standard

The code rules in [implementation and audits](implementation-and-audits.md) say what
a file must explain: the problem, the approach, the invariants, the contract. This
reference says how to explain it. The standard is code that engineers read to learn
from: the Menhir parser generator and the GNU C library are examples (see the
[reading list](#reading-list)). In those files, a comment is an
argument written for a colleague. It defines its terms, it states a claim, it says
why the claim holds, and it says what the code does with it.

The comments are prose: full sentences, in paragraphs, in the order that a reader
needs them. A section of code opens with a paragraph that says what the section does
and why it exists. "We" is the author and the reader, reasoning together.

## Explanation moves

Use the move that the code needs. A simple function needs none of them.

1. **Define before you use.** Introduce the notation and the terms of a section
   before the first sentence that needs them.

   ```ocaml
   (* We write [a ~> b] when task [a] must finish before task [b] starts.
      A schedule is valid when it orders every pair [a ~> b]. *)
   ```

2. **Argue: claim, reason, consequence.** State what is true, why it is true, and
   what the code does because of it. The consequence is the part that the reader
   cannot get from the code alone.

   ```python
   # Every key in `pending` is also in `index`: insert() adds to both, and only
   # commit() removes from `pending`. So the lookup below never misses, and we
   # do not need a fallback path.
   ```

3. **Prove the invariant at the site.** Where the code relies on an invariant, give
   its argument. Name the module that guarantees each precondition.

   ```typescript
   // The queue holds no cycle, so this traversal terminates. Indeed, a cycle
   // would need a job that depends on itself, and `Scheduler.add` rejects such
   // a job before it reaches the queue.
   ```

4. **Justify a choice where it is made.** Name the alternatives, the one chosen, and
   what it buys. The file header does this for the whole design; a local comment
   does it for a local choice.

   ```c
   /* We could report the event before or after the state changes. We report it
      after: the handler then sees the new state, and the event needs to carry
      only the old one. */
   ```

5. **State the scope of a claim.** Write the assumptions under which the claim holds,
   next to the claim.

   ```python
   # Two runs give the same output. This holds only when the clock is injected:
   # the default clock reads the system time.
   ```

6. **Say what is not known.** When you do not know why something is so, write that.
   Then say what is known. Never write a reason that you did not check.

   ```ocaml
   (* The vendor API returns the last page twice when the cursor is empty. We do
      not know why; we observed it on 2026-10-04 (kb/external/vendor.md). We drop
      the duplicate here. *)
   ```

7. **Give a reading path.** When a function is general, tell the reader which simple
   case to read first.

   ```typescript
   // On a first reading, take `batch` to be 1: the function then sends one
   // message and waits for its acknowledgment. Larger batches only change
   // when the acknowledgment is awaited.
   ```

8. **Warn of traps.** Say when a declaration is misleading. Say when a name means less
   than it seems. List all the exceptions to a rule.

   ```c
   /* This struct is a view, not an allocation: its fields are read at fixed
      offsets from a base pointer. Two exceptions to the layout below: ... */
   ```

9. **Document data as carefully as code.** Give each field its meaning and its unit.
   Give its lifecycle: set once, changed by one owner, or transient. Draw a bit-level
   or byte-level representation in ASCII.

   ```ocaml
   mutable mark: Mark.t;
     (* A transient mark, used only during a traversal; meaningless outside one. *)
   ```

10. **State the properties of a function or a group.** Write each precondition
    above the function, such as `Here, the input CAN be empty`. For a group, say
    which functions raise, which are tail recursive, and what each one costs.

    ```python
    # The functions below never raise, and each one runs in O(1): the tables are
    # computed once, in __init__.
    ```

11. **Label arguments whose role is not visible.** At a call with positional
    arguments or continuations, name each role.

    ```ocaml
    Table.action state token
      shift     (* when the table says shift *)
      reduce    (* when the table says reduce *)
      fail      (* when the table has no entry *)
    ```

12. **Cite the source.** For a known algorithm or a protocol rule, give the paper or
    the book and page. For a standard, give the RFC section or the clause.

13. **Keep a past decision that still constrains the code.** Sometimes the present
    shape makes sense only with a past decision. Explain that decision, with its date.
    Narrate no other history: that goes in the commit message.

    ```typescript
    // 2026-03-02: we let callers build a Session from a token (Session.ofToken).
    // For this reason, Session stays generic in its user type, although every
    // caller in this repository passes the same type.
    ```

## What a comment must not do

- Restate the next line.
- Use hollow words: "robust", "properly", "appropriately", "gracefully", "as needed",
  "handles edge cases", "for safety". Name the case, the property or the failure.
- Replace the explanation with a KB ID. Write the claim, then the ID.
- Narrate history: "new approach", "fixed", "now handles".
- Apologize for a design. When a comment must be long because the design is
  confused, change the design.

`comment-check.py` warns on hollow words and on comments that hold only KB IDs:

```sh
python3 tools/comment-check.py src
```

## The explanation pass

A model that writes correct code does not always write a good explanation. Run an
explanation pass on the judgment tier after the step's tests pass, before Phase 5.
Run it on each non-trivial changed file: a kernel, an algorithm, a data
representation, concurrent code or a protocol.

1. Read the file as it is now, without the plan.
2. Write the header and the section paragraphs from the top: the problem, the idea,
   the invariants, and their argument. Then the local moves that the code needs.
3. When the explanation is hard to write, the design is usually the cause. Garden the
   file ([implementation and audits](implementation-and-audits.md)), then explain it.
4. Commit the pass alone: `explain: <file>: <what is now explained>`.

## The cold read

The Phase 5 cold read gives a fresh reviewer one changed file, without the KB, the
plan or the author. The reviewer answers:

1. What problem does this file solve, and what does it not do?
2. What is the key idea, and which alternative did the author reject?
3. Which invariants does it keep, and why does each one hold?
4. Which preconditions does it rely on, and who guarantees them?
5. What breaks first if the main invariant fails?
6. Which part is a trap for the next maintainer?

The author compares the answers with the truth. Each wrong or missing answer is a
finding, located where the reader got lost.

## Measure it

To know whether the explanations improve, measure them. At each milestone, choose
up to five non-trivial files changed in it, and run the cold read. Score each of the
six answers as right, partial, wrong or missing. Write the scores in
`kb/reports/cold-read-<milestone>.md`, and compare them in the milestone
retrospective. A score that does not improve is a finding: the cause is the moves, the
explanation pass, or the tier that runs it.

## Reading list

Read these files as examples of the standard. They are not copied here.

- Menhir, `middle/LoopDetection.ml`: notation first, a cited theorem, a claim with its
  argument, the scope of a claim, and a reading path for a general function.
  <https://gitlab.inria.fr/fpottier/menhir/-/blob/master/middle/LoopDetection.ml>
- Menhir, `lib/Engine.ml`: an LR engine explained step by step. Local design choices
  with their alternatives, preconditions above each function, labeled continuations,
  dated notes on decisions that still shape the types, and an honest "unclear".
  <https://gitlab.inria.fr/fpottier/menhir/-/blob/master/lib/Engine.ml>
- Menhir, `middle/LR0Construction.ml`: the data of a graph traversal, with each field's
  lifecycle, and the argument that a traversal terminates.
  <https://gitlab.inria.fr/fpottier/menhir/-/blob/master/middle/LR0Construction.ml>
- GNU C library, `malloc/malloc.c`, the section "Chunk representations": a memory
  layout drawn in ASCII. It also warns about a misleading declaration and lists all
  the exceptions.
  <https://sourceware.org/git/?p=glibc.git;a=blob;f=malloc/malloc.c>

## What is not checked

`comment-check.py` finds some bad comments; it cannot find a missing or a wrong
explanation. The cold read finds those, and its scores show the trend. A share of
comment lines is not a target. In the files above, comments hold half of the text or
more. The cause is that the code needs that much explanation; no ratio asked for it.
