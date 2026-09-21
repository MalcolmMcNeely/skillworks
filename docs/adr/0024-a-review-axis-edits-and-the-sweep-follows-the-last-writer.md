# A review axis edits, and the sweep follows the last writer

Each of the three review axes runs as a step of the loop, in a session of its own. They were readers:
an axis reported a finding and the finishing step made the change. That throws away the session that
already has the finding in hand and hands the work to one that does not, so an axis now fixes what it
finds. The driver takes a reading of the worktree before and after each axis step, works out what
changed, and carries that to the step that reconciles, so an edit no session announced still cannot
reach a commit unnoticed. Comment sweeping moves to the end, because every step that writes runs
after the place it used to sit, and each one could put back what it had just cut.

The loop runs seven steps:

```
build → standards → spec → architecture → fix → sweep → finish
```

`build` starts the session and leaves its change uncommitted. The three axes each run fresh, read the
change, report under their own heading and may fix what they find. `fix` resumes the build session
and reconciles: it holds all three reports and all three records, and it is the only step that sees
the whole picture. `sweep` runs fresh and writes last. `finish` resumes the build session, runs the
suite, commits and closes.

## Considered options

**An axis stays a reader, and a check proves it touched nothing.** This was the first answer, and it
is enforceable rather than merely asked for: `claude -p` takes `--permission-mode plan`, which blocks
every edit, and `--disallowedTools "Edit" "Write" "NotebookEdit"`, which removes those tools from the
session's context entirely. Rejected because fixing what it finds is the point of giving an axis a
session of its own. An axis that can only report makes the finishing step retype work already
understood somewhere else.

**An axis names its own edits in its report.** Rejected. It is an instruction, and a step written
into a skill can be skipped. The check that guards an axis step reads only for its heading, so it
cannot tell a report that named its edits from one that did not, and a silent edit is the failure
being closed. The driver knows for certain what changed, so nothing is gained by asking a session to
remember.

**A later axis is told what the axes before it changed.** It would stop two axes undoing each other.
Rejected because that influence is what the three-way split exists to prevent: each axis runs fresh,
with no `--resume`, so that none of them reads another's mind. It also only half works, because
nothing follows the last axis. Reconciling belongs in `fix`, which has every report and every record.

**The sweep runs inside the finishing step.** One fewer step and one fewer session. Rejected by the
rule this repository already holds: a step written into a skill can be skipped, and a step in the
script cannot. The sweep guards a rule, so it cannot be the skippable kind.

**The sweep runs after the commit.** It would leave the sweep genuinely last. Rejected because the
finishing step closes the ticket, so the sweep would tidy a ticket already reported done, add a
second commit to it, and leave the suite having run before the last edit.

## Consequences

This replaces one sentence of [ADR 0004](0004-steering-rules-are-data-a-test-enforces.md), the one
recording the loop as sweep and review in one resumed session ending in `/code-review`. The other two
sentences of that paragraph stand. *"A step written into a skill can be skipped, and a step in the
script cannot"* is the rule that decided two of the options above. *"Run by hand with no flag,
`/implement` still does every step itself"* is true again, because the hand run gains a reviewing
section and a fixing section of its own and so mirrors the loop.

The axes are ordered, and ordering now matters. `standards` edits before `spec` and `architecture`
read, so its work is seen by two more axes, and `architecture` edits after every other axis has
finished, so its work is seen by none of them. `fix` and the suite both run after all three, which is
what makes the asymmetry affordable rather than dangerous.

`fix` and `finish` resume the build session. The three axes and the sweep do not. The sweep losing
its `--resume` is a gain as well as a move: reading the change cold, it sees the whole ticket, where
a sweep resumed in the build session only ever saw what that session had written.

The two halves are called `fix` and `finish` because the obvious names were taken. Closing already
means removing a worktree and its branch, and `land-ticket.sh` already has a `resolve` step for a
rebase that conflicts.
