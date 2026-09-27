# The driver counts the Verdicts and builds its own Gaps

The drift check was one Session that read the spec, every ticket and the whole diff at once, then
wrote a report in prose. A model with that much in its context leaves things out and still sounds
sure, and nothing read the report but the Session that drove the loop. A story it skipped, or found
Missing, stayed that way, and with the files Tracker the driver closed the spec anyway.

So the spec numbers every story and every implementation decision, and names every Surface, in a
shape the driver checks before the first ticket runs. The drift check still judges, and writes one
Verdict for each item. The driver judges nothing: it counts the Verdicts against the spec. An item
Missing, Partial or Out of step, or with no Verdict, or with two, is a Gap. The driver files the Gaps
as one ticket under the spec, built by the usual steps, and asks the drift check about those items
again. The loop has one round of this. A Gap left after it stops the loop, and so do a Contradicts
and a report with no Verdicts, because each needs a person.

Names get a judge of their own, the Name check, which runs after the Gaps are built and reads only
the diff and the glossary. A name is the one finding no count can check, since nothing lists the
names that should have changed, so its judge gets the smallest context. The loop makes every rename
it lists in a ticket of its own, and a smaller Name check confirms each one was made.

The full run moves to the end, after both judges and both tickets, and runs once. A clean finish is
now the driver's call: every item Done or In step, every rename made, and the full run green.
Unrequested work stops nothing, and the driver names each item in the log for a person to read.

## Considered options

**Let the Session that drives the loop keep reading the report.** Rejected. It judges a second time,
in a second place that can disagree with the first, and it had already let Gaps through.

**One judge for the spec and the names.** Rejected. The judge with the most to read is the one most
likely to drop a name, and a dropped name is the one miss nothing else can catch.

**A second round, or a round for each kind of finding.** Rejected. One round is small enough to
reason about, and a Gap that survives a build aimed at it is a question for a person.

**A full run after each Gap ticket and rename ticket.** Rejected. The full run is the slowest part of
the loop, and each ticket already passes its own Suite step before it Lands.

## Consequences

The drift check and the Name check can run on work the full run later finds red. Their work is then
thrown away, which costs less than a second full run.

A spec written before this change cannot be counted, and the loop turns it down before any ticket
runs.
