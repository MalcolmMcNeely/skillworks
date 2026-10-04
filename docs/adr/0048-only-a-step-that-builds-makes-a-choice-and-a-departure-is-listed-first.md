# Only a step that builds makes a Choice, and a Departure is listed first

This supersedes the part of ADR 0047 that lets every loop Session make a Choice, and the part that
has Finishing tell a fault in a `CHOSE` line. The rest of ADR 0047 stands.

A Choice is made only where the ticket and the spec leave more than one way open. A point either of
them names is not open, and a part that only touches the point does not open it. Only a step that
builds makes a Choice or names a Hand check: the build, `fix` and the Cut. A review that finds the
change differs from the ticket has a finding. The drift check and the Name check give Verdicts.

A question the ticket tells the Session to ask a person is a Choice. The build answers it, and the
question never keeps the ticket open: Finishing closes it, with the question and the answer in the
Closing note.

Where two parts that both name one point disagree, the build takes the stricter one and writes a
line that starts with `DEPARTS`. Finishing writes the same line for a fault it may not fix. The
driver lists every `DEPARTS` line above the Choices, and the loop goes on. It hands the build's
`DEPARTS` lines to the spec review and the drift check, and each judges whether the rule held. Where
it held, the drift check gives the part that lost `Contradicts`, so the spec stays open until a person
mends it. Where it did not, the spec review has a finding and fixes it.

A Hand check needs one of three things no Session has: a real device, a real outside account or
service, or a person's eyes on the screen or the page. The Suite is never one, and a question is never
one. The driver hands `fix` the lines the build wrote, so each line is written once and the list at
the end of the run shows it once.

## Why

The runs of 3 and 4 October showed every Session using the Choice it was offered. In one run a build
took a quantity of 0 that the ticket and the spec both turned down, and wrote a `CHOSE` line for it.
The spec review backed it with a `CHOSE` of its own and no finding, and the drift check gave the
decision `Done`. The change Landed, and the only sign was three of the 33 lines at the end of the run.
A judge that may choose chooses its way out of a finding.

In a drill whose ticket said to ask the developer before it closed, one run closed the ticket and the
other stopped as Blocked at Finishing, with the work built and not Landed. The same words gave two
ends, because Finishing had no word for a question.

Of three Hand checks in the full run, two were checks a Session could run: a read of the code, and
the Suite. Every step repeated the Choices and Hand checks it was handed, so 2 Choices were listed as
5.

## Considered options

**Every step may still choose, told that a Choice never goes against the ticket.** Rejected. It asks a
judge to hold back, and the run showed it did not.

**A build that sees two readings stops as Blocked.** Rejected. In the run the two parts did not
disagree: one named the point and the other only touched it. A stop there throws away sound work for
a clash that was not real.

**A Departure stops the loop.** Rejected. The build departs only by the rule, so the work is sound. The
top of the list is where a person sees it.

**A question in a ticket is Blocked at the build.** Rejected. It stops the loop for a question with a
safe answer, as both drill runs found.

**A Hand check is any check a Session cannot do with its tools.** Rejected. A Session that did not try
may answer that it cannot. A closed list of three kinds is something it can match.

**The drift check gives the part that lost `Done`.** Rejected. A spec that rules two ways on one point
is a fault only a person can mend, and a closed spec keeps the clash for its next reader.

**The driver drops repeated lines by their text.** Rejected. A Choice comes back in different words at
each step, so no match on text finds the repeat.

## Consequences

The driver sends each kind of step its own words: the steps that build get the Choice, the Departure
and the Hand check, the reviews get none of them, and Finishing gets the Departure for a fault it
tells and the words that a question never keeps a ticket open.

A true clash in a spec now ends a run with the work on the Target branch and the spec open, and a
person mends the spec.

Whether a Session follows the new words is shown only by a run. The two cases that showed the faults
are run again after the change Lands, three times each, and the spec that makes the change holds
their pass bar.
