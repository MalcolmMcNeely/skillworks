# The Name check

Part of [the Dev loop](../the-loop.md).

The drift check asks whether the work is there. The **Name check** asks one smaller thing: whether
the names still say what the code means. A small question in a small context misses less.

It runs once, after the drift check and its count, or after [the Gap
round](drift-check.md#the-gap-round) when the count found a Gap, so it sees every name the spec
brought in, the Gap ticket's too. The script opens one more worktree and runs
`/skillworks:spec-names <spec> <base>` in a Fresh Session. It reads two things, and nothing else:

- the commits the spec's tickets Landed after the base commit, through `spec-commits`, in place of
  the spec's whole diff. A commit with no `Ticket:` trailer is not read, and neither is another
  spec's work;
- the glossary of each context those commits touch, as `CONTEXT-MAP.md` names it, or your one
  `CONTEXT.md`.

It lists two kinds of finding, and each one is a rename:

- a name whose meaning moved: the code under it now does something else, and the name stayed;
- a concept two tickets named two ways.

A name is a finding only while it still stands on the Target branch. The check searches the Target
branch before it lists a name, so a name a later commit renamed or removed never becomes a rename
ticket with nothing to change.

A rename is never "Optional". A name that says the wrong thing is work owed, and nobody is asked
whether to fix it.

## The Name report

The Session records a **Name report** with the spec, as the drift check records its report, through
`tracker-publish names` with either Tracker. With the GitHub Tracker it is a new comment on the spec
issue, and a rerun adds another comment below it. With the files Tracker it goes at the end of
`spec.md`, below the drift report. A new drift report takes an old Name report away, because a new
drift check starts the judging again.

```markdown
## Name report

### Renames

- `Batch`: it now names a whole run of tickets, and the glossary calls that a Job.
```

The report opens with `## Name report`, then a `### Renames` list, one line per finding. Each line
names the name or the concept and says in one sentence why it must change. A concept the glossary
has no word for says `no glossary word` on its line. With nothing to rename, the list says `- None`.

The script reads the report back from the Tracker, so a finding the Session only said and never
recorded is caught. It keeps a copy at `.spec-loop/<spec>/names.md`, beside `drift.md`, and writes a
`NAME` line for each rename. No report stops the loop, and so does a report with no `### Renames`
list.

With no rename there is no rename ticket and no Name re-check, and the loop goes on to the full run.

## The rename ticket

When the Name report lists a rename, the loop makes it. You do not have to ask for a ticket.

The script writes one **rename ticket** from a fixed template and with no model: one entry for each
line of the `### Renames` list, quoting the line. The acceptance criteria are the renames. The
Tracker files it under the spec, the way it files [the Gap ticket](drift-check.md#the-gap-round), and
the loop builds it through [the same steps](steps.md) as every other ticket. It comes after the Gap
ticket, so no later build brings in a new bad name.

The build takes the glossary's word for a concept when the glossary has one. When the glossary has
none, it takes the name the code and the spec use most, and the script writes a `NOTE` line saying
the concept has no glossary word. The build never edits a glossary. A new word is settled in a grill.

## The Name re-check

After the rename ticket Lands, the script runs the Name check again, on the rename ticket alone:
`/skillworks:spec-names <spec> <base> <rename ticket>`. It reads the rename ticket's list and the
diff of that ticket's commits, and nothing else. It records a new Name report with a `### Verdicts`
list, one line for each rename:

```markdown
## Name report

### Verdicts

- Batch: Done
- Gap and Hole: Not done. Hole is still the name in two files.
```

Each rename is Done or Not done, and a Not done carries one sentence of reason. The script keeps a
copy at `.spec-loop/<spec>/names-renames.md` and counts it the way it counts the drift check's
Verdicts. A rename with no Verdict, or with two, counts as not made. A Verdict for a rename the
ticket does not owe gets a `WARN` line and counts for nothing. A rename not made stops the loop and
names it, as [When a step fails](stops.md) shows. With every rename Done, the
loop goes on to the full run.
