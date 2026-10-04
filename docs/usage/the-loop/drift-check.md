# The drift check

Part of [the Dev loop](../the-loop.md).

Every ticket passed its own acceptance criteria. Nothing so far has asked whether all of them together
are what the spec wanted.

So when no open ticket is left, the script opens one more worktree and runs
`/skillworks:spec-drift <spec> <base>` in a Fresh Session. It judges the work against the spec, not the
tickets, because a ticket that drifted still passed its own criteria. It records one report with the
spec, under the heading `## Drift report`, through `tracker-publish drift` with either Tracker. With
the GitHub Tracker the report is a new comment on the spec issue, and a rerun adds another comment
below it. With the files Tracker there is no issue, so the report goes at the end of the spec's
`spec.md`.
The script then reads the report back from the Tracker and keeps a copy at
`.spec-loop/<spec>/drift.md`.

The drift check reads the spec's commits through `spec-commits`: the commits after the base commit
that the spec's tickets Landed, the Gap ticket's among them. A commit is the spec's only when its
`Ticket:` trailer names one of the spec's tickets, so a commit with no `Ticket:` trailer is not read,
and neither is another spec's work. A hand fix that should count for the spec carries the trailer of
one of its tickets, such as `Ticket: #<n>`, or `Ticket: <spec>/<n>` with the files Tracker.

The spec's commits show where the work is. The Verdict judges the newest Target branch as it stands,
so a story done by a hand fix or by another spec counts as Done, and code from any source that does
what the spec ruled out is Contradicts. Unrequested work and two names for one idea come only from
the spec's commits, and an item is listed only while it still stands on the Target branch.

The drift check reads every `DEPARTS` line the spec's builds wrote, in this run and in any earlier run
on the same spec. The script reads them from the Journal. A build writes a `DEPARTS` line when two
parts of the ticket or the spec name one point and disagree, and it takes the stricter one. The drift
check asks two things of each line: do both parts really name the point, and was the stricter one
taken? Where the rule held, the part that lost gets Contradicts, so the loop stops at the end with the
spec open. The Departure is the reason on that Verdict, and you mend the spec. Where the rule did not
hold, the item gets the Verdict the code earns.

When your team has a README Surface, the drift check reads the README on every spec, even a spec with
no README item. The README Surface is the Surface headed `## The README` in
`docs/agents/surfaces.md`, and its "Where it lives" gives the README's path. A link, path or command in
the README that the spec removed, renamed or moved makes the README Out of step, and the reason names
it. The count treats that Verdict as an item of the spec, so an Out of step README, or a README with
no Verdict, is a Gap. The Gap ticket fixes only the broken line, within what the Surface's "What to
capture" allows. With no README Surface, a README Verdict on a spec with no README item gets a `WARN`
line and counts for nothing, like any other name the spec does not hold.

## Verdicts

The report opens with a `### Verdicts` list. It gives every item of the spec one **Verdict**, on a
line of its own: `- S2: Missing. No code reads the report.` A story is `S<n>`, a decision is `D<n>`,
and a Surface is its bold name. Each story and decision gets one of four Verdicts:

| Verdict | What it means |
|---|---|
| Done | The code does what the spec asked. |
| Partial | Some of it is there, and the report says what is not. |
| Missing | None of it is there. |
| Contradicts | The code does something the spec ruled out. |

Each Surface gets **In step** or **Out of step**. Every Verdict other than Done or In step carries one
sentence of reason. The list holds Verdict lines and nothing else, because the script reads every
bullet under that heading down to the next heading.

The prose follows under headings of its own. `### Notes` says what each Partial, Missing and
Contradicts lacks or breaks. `### Surfaces` says what each Out of step Surface lacks. `### Glossary`
holds a look for two tickets that brought in two names for one idea, with your glossary as the
judge. Last comes a `### Unrequested` list: work the spec never asked for, one item per line.

## The count

The drift check judges. The script does not. It counts the Verdicts against the items it read from
the spec before the first ticket, so an item the drift check skipped is caught by arithmetic.

A **Gap** is an item the spec asked for that is not proved done:

- an item with a Verdict of Missing, Partial or Out of step;
- an item with no Verdict;
- an item with more than one Verdict, because two Verdicts that disagree never pass as one.

A Verdict that names no item of the spec, such as a typo, gets a `WARN` line and counts for nothing.
Each Unrequested item gets a `NOTE` line. Unrequested work never stops the loop.

The loop stops, and the spec stays open, when:

- the drift check recorded no report, after two Nudges. A drift check that recorded no report is
  Nudged first: the script resumes the same Session in its own worktree, and names what is missing
  and the `tracker-publish drift` command that records it. Each Nudge writes a `NUDGE` line;
- the drift check began its last message with a `BLOCKED` line. It does so when a Steering file it
  reads is missing, or when `spec-commits` or `tracker-publish drift` refused twice. The loop stops
  at once, with no Nudge, as [When a step fails](stops.md) shows;
- the report has no `### Verdicts` list;
- any Verdict is Contradicts. The stop line names each Contradicts and every Gap beside it, because a
  person decides on a part of the spec the code ruled against. The loop stops at the count, before any
  Gap is built;
- any Gap is left after [the Gap round](#the-gap-round). The stop line names each one.

The drift check fixes nothing and closes nothing. A fix is new work, and the loop files it as a ticket
of its own.

## The Gap round

When the count finds a Gap and no Contradicts, the loop builds the Gaps itself. You do not have to
ask for a ticket.

1. **The Gap ticket.** The script writes one ticket for every Gap, from a fixed template and with no
   model. For each Gap it quotes the item's text from the spec, its Verdict and the reason. An item
   with no Verdict, or with two, reads "The drift check did not judge this exactly once. Check it,
   and build it if it is not there.", so work already done is not built twice. The acceptance
   criteria are the Gap items. The Tracker files it under the spec: a sub-issue with the
   `ready-for-agent` label with GitHub, and a new file in the spec's `tickets/` folder with files.
2. **The build.** The loop reads the open tickets again, finds the Gap ticket, and builds it through
   [the same steps](steps.md) as every other ticket, then Lands it.
3. **The re-check.** The script runs the drift check again, on the Gap items alone:
   `/skillworks:spec-drift <spec> <base> S4, The user docs`. It reads the same spec's commits as the
   first drift check, the Gap ticket's now among them. A small context misses less. The
   report is kept at `.spec-loop/<spec>/drift-gaps.md`, and the script counts it against those items
   only.

There is one round. A Gap that survives a build aimed at it comes to you rather than looping, so a Gap
left after the re-check stops the loop and names each one. A Contradicts in the re-check stops it too,
and so does a re-check that recorded no new report after two Nudges, because the Gap items were not
judged again. A re-check that recorded no new report is Nudged first, as the drift check is.
