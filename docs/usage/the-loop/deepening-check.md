# The Deepening check

Part of [the Dev loop](../the-loop.md).

Every ticket passed its own reviews. Nothing so far has looked at the spec's work as a whole for
modules it left shallow.

So when no open ticket is left, and before [the drift check](drift-check.md), the script opens one
more worktree and runs `/skillworks:spec-deepening-check <spec> <base>` in a Fresh Session. The Session is told
to run only Trials, as the drift check is. It changes no code. It records one report with the spec,
under the heading `## Deepening report`, through `tracker-publish deepening-check` with either Tracker. With the
GitHub Tracker the report is a new comment on the spec issue. With the files Tracker the report goes
at the end of the spec's `spec.md`, above any drift report. The script then reads the report back from
the Tracker and keeps a copy at `.spec-loop/<spec>/deepening-check.md`, beside `drift-check.md` and `name-check.md`.

## What it reads

The Deepening check reads the spec's commits through `spec-commits`: the commits after the base commit
that the spec's tickets Landed. A commit with no `Ticket:` trailer is not read, and neither is another
spec's work, so code another spec or a person wrote is never judged here.

It judges those commits with the deep-module vocabulary of `codebase-design` and its deletion test:
would deleting a module concentrate its complexity in one place, or just move it? It reads the
glossary, so it names each module in your domain's words, and it reads the ADRs in the folder
`adr-folder` names. It asks nobody anything.

## The report

The report opens with a `### Strong` list, one line for each Strong candidate:
`- <module>: <the problem>. <the deepening>.` With nothing Strong to file, the list says `- None`.
What counts as Strong is in `docs/skillworks/deepening-check.md`, your team's
[Steering file](../steering.md) for this check.

The prose follows under headings of its own: `### Over the limit` for the Strong candidates past the
limit, `### Worth exploring` and `### Speculative` for the weaker ones, and `### ADR` for each
candidate that goes against an ADR. Read these to see what was not built.

## The candidates that go against an ADR

An ADR records a decision a person made, and the loop never reopens one. A candidate that goes
against an ADR is never in the `### Strong` list, whatever its strength. The report lists it under
`### ADR`, with the ADR's number and the reason, so you can decide whether to reopen that ADR in a
grill.

## The limit

`limit` in the YAML block at the end of `docs/skillworks/deepening-check.md` is the most deepening
tickets the loop files for one spec. It is 3 unless your team changes it. The judge ranks the Strong
candidates, strongest first. The script counts: a `### Strong` list longer than the limit gets a
`WARN` line, and only the first lines up to the limit are filed. A file whose YAML block names no
whole `limit` stops the loop before the check runs, and names setup.

The limit holds for the whole spec, and not for each run, because the check runs once for each spec.

## Once for each spec

The Deepening check runs once for each spec, so a rerun finishes what the first run started and files
no more tickets. Before it runs the check, the script looks on the Tracker for a deepening ticket under
the spec, open or closed. It knows one by its title, `TICKET: Deepen <module>`. When it finds one, it
does not run the check again. It writes a `deepening-check` line that names each one it found, and it builds
each one still open as it builds any open ticket.

A check that filed no ticket still leaves its report on the Tracker. When the script finds no
deepening ticket but finds a Deepening report, it does not run the check again either. It writes a
`deepening-check` line that says the spec already holds the report, and it reads that report as if the check
had just recorded it. A report that says `- None` files nothing. A report whose `### Strong` list
names candidates files them up to the limit, which is what a first run that stopped before it filed
them owes.

## Turning it off

Set `limit: 0` in `docs/skillworks/deepening-check.md` to turn the Deepening check off. A check that
is off does not run, and the log gets a `NOTE` line that says so:

```
2026-09-28 18:24:10 NOTE  the Deepening check is off, because docs/skillworks/deepening-check.md sets limit to 0
```

A dry run shows the `deepening-check` step as off, and shows no `deepening-ticket` line.

## The deepening tickets

The script writes one deepening ticket for each line of the `### Strong` list, up to the limit, from a
fixed template and with no model. Its title is `TICKET: Deepen <module>`. It quotes the report's line,
and that line is its acceptance criterion. The Tracker files it under the spec, the way it files
[the Gap ticket](drift-check.md#the-gap-round).

The loop reads the open tickets again, and builds each deepening ticket through
[the same steps](steps.md) as every other ticket, with a build Session of its own, then Lands it. A
failed one stops the loop as any failed ticket does, and [the Keep and the restart](stops.md) work as
they do for any ticket. Then the drift check, the Gap round, the Name check and the full run follow.

The list at the end of a run names each deepening ticket the run built.

## When it stops the loop

The loop stops, and the spec stays open, when:

- the Deepening check recorded no report, after two Nudges. A check that recorded no report is
  Nudged first: the script resumes the same Session in its own worktree, and names what is missing and
  the `tracker-publish deepening-check` command that records it;
- the Deepening check began its last message with a `BLOCKED` line. The loop stops at once, with no
  Nudge;
- the report has no `### Strong` list. No Nudge is sent;
- a deepening ticket failed.
