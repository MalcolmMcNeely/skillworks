# The Simplify check

Part of [the Dev loop](../the-loop.md).

Every ticket passed its own reviews, and those reviews judged whether the code works. Nothing so far
has looked at the spec's work as a whole for code it made harder than it has to be.

So after [the Deepening check](deepening-check.md) and every deepening ticket it filed, and before
[the drift check](drift-check.md), the script opens one more worktree and runs
`/skillworks:spec-simplify-check <spec> <base>` in a Fresh Session. The Session is told to run only
Trials, as the drift check is. It changes no code. It records one report with the spec, under the
heading `## Simplify report`, through `tracker-publish simplify-check` with either Tracker. With the
GitHub Tracker the report is a new comment on the spec issue. With the files Tracker the report goes at
the end of the spec's `spec.md`, below any Deepening report and above any drift report. The script then
reads the report back from the Tracker and keeps a copy at `.spec-loop/<spec>/simplify-check.md`, beside
`deepening-check.md` and `drift.md`.

## What it reads

The Simplify check reads the spec's commits through `spec-commits`: the commits after the base commit
that the spec's tickets Landed, the deepening tickets' among them. A commit with no `Ticket:` trailer
is not read, and neither is another spec's work, so code another spec or a person wrote is never
judged here. It judges only the lines those commits wrote or changed.

## The four angles

It judges those lines from four angles. Your team's
[Steering file](../steering.md) for this check, `docs/skillworks/simplify-check.md`, says what each
one covers, and holds your team's own checks and what never to report:

- **Reuse.** Code that writes again what the codebase already has.
- **Simplification.** Code harder than its job.
- **Efficiency.** Code that does work it does not need.
- **Altitude.** Code at the wrong level.

It hunts no correctness bugs, it never calls Claude Code's `/simplify`, and it asks nobody anything.

## The report

The report opens with a `### Findings` list, one line for each finding:
`- <where it is>, <angle>: <the problem>. <the simpler form>.` With nothing found, the list says
`- None`, and the loop goes straight on to the drift check.

## The simplify ticket

When the `### Findings` list holds a line, the script writes one simplify ticket from a fixed template
and with no model. Its title is `TICKET: Make the cleanups the Simplify check found`. It quotes every
line of the list, and each line is an acceptance criterion. The Tracker files it under the spec, the
way it files [the Gap ticket](drift-check.md#the-gap-round).

The loop reads the open tickets again, and builds the simplify ticket through
[the same steps](steps.md) as every other ticket, with a build Session of its own, then Lands it. A
failed one stops the loop as any failed ticket does, and [the Keep and the restart](stops.md) work as
they do for any ticket. Then the drift check, the Gap round, the Name check and the full run follow.

The list at the end of a run names the simplify ticket the run built.

## Once for each spec

The Simplify check runs once for each spec, so a rerun finishes what the first run started and files
no more tickets. Before it runs the check, the script looks on the Tracker for the simplify ticket
under the spec, open or closed. It knows the ticket by its title. When it finds it, it does not run
the check again. It writes a `SIMPLIFY` line that names the ticket, and it builds the ticket if it is
still open, as it builds any open ticket.

A check that filed no ticket still leaves its report on the Tracker. When the script finds no
simplify ticket but finds a Simplify report, it does not run the check again either. It writes a
`SIMPLIFY` line that says the spec already holds the report, and it reads that report as if the check
had just recorded it. A report that says `- None` files nothing. A report whose `### Findings` list
names findings files the simplify ticket, which is what a first run that stopped before it filed the
ticket owes.

## Turning it off

Set `enabled: false` in `docs/skillworks/simplify-check.md` to turn the Simplify check off. A check
that is off does not run, and the log gets a `NOTE` line that says so:

```
2026-09-28 18:31:40 NOTE  the Simplify check is off, because docs/skillworks/simplify-check.md sets enabled to false
```

A dry run shows the `simplify-check` step as off, and shows no `simplify-ticket` line.

## When it stops the loop

The loop stops, and the spec stays open, when:

- the Simplify check recorded no report, after two Nudges. A check that recorded no report is Nudged
  first: the script resumes the same Session in its own worktree, and names what is missing and the
  `tracker-publish simplify-check` command that records it;
- the Simplify check began its last message with a `BLOCKED` line. The loop stops at once, with no
  Nudge;
- the report has no `### Findings` list. No Nudge is sent;
- the simplify ticket failed.
