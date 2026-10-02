# A loop Session makes its own Choices, and only work it cannot do stops the loop

A loop Session has nobody to ask, so it never waits for a person. Where its ticket leaves more than
one way open, it makes the Choice itself and says so in a line that starts with `CHOSE`. Where the
ticket asks for a check no Session can run, it names a Hand check in a line that starts with
`HAND CHECK`, and the ticket still Lands. It begins its report with a line that starts with `BLOCKED`
only when it cannot do the work: a Denial it cannot get past, or a ticket with nothing left to build.

The driver reads those three lines and no other words. A Blocked step stops the loop at once, at
the step that says it, with its Denials and with no Nudge. The driver copies each Choice and each
Hand check into the log, and lists them all when the run ends, so the developer reads what was
chosen and what is theirs to run.

A Nudge tells a Session that put a choice to a person to make that Choice itself, within what its
step allows. In Finishing, a fault the Session may not fix is closed and told: no edit is made, the
Closing note and a `CHOSE` line name the fault, and the ticket Lands.

This adds to ADR 0033. That one says which checks earn a Nudge. This one says what a Nudge tells a
Session that asked, and names the one stop a Nudge respects.

## Why

The spec holds the design decisions that matter, and the Steering files hold the team's rules. What
is left for a Session to choose is small, and the reviews, the Suite and the drift check judge what
it chose against the spec. A loop that waits for an answer waits for ever.

The loop's own records showed the cost of the other way. Sessions put choices to a person in plain
words, with a recommendation, and the driver read none of it. One build that asked passed its check,
and nine more steps ran before the loop stopped. One Nudge said to close a ticket, and so settled a
choice against the Session's own recommendation. And a ticket whose app check no Session could run
closed with that check named in its Closing note, and Landed: the developer ran the check
afterwards. That last case is the behaviour this decision makes the rule.

## Considered options

**Blocked covers any block, a choice included.** Rejected. It stops the loop for a person's answer
to a question the Session could have settled, and a rerun then builds the ticket again from nothing.

**The driver looks for question words in a last message.** Rejected. No last message in the records
ended in a question mark, so the match would be on words such as "pick one". Those words also end a
report whose work is done, so the match stops good loops and still misses some bad ones. An exact
line is a fact the driver can read without judging.

**Carry on to Finishing after a Blocked build.** Rejected. The ticket cannot Land, and a rerun never
reads the Kept work, so the six steps after the build are spent for nothing.

**A Nudge names Blocked as the answer for a choice.** Rejected for the same reason as the first
option: it turns a choice into a stop.

**In Finishing, the Session fixes the fault it found.** Rejected. No Suite runs after Finishing, so
that edit would Land unproved. A known fault that is told is safer than an unknown edit.

**A fault found in Finishing is Blocked.** Rejected. A rerun builds the ticket again and can make the
same fault again, and the loop has stopped for something a later ticket can mend.

**The Closing note alone carries Choices and Hand checks.** Rejected. It is written only in
Finishing, a Choice can be made at any step, and reading every note back is a model's judgement
where a copied line is a count.

## Consequences

A ticket can Land with a fault that Finishing saw, or with an acceptance criterion no Session could
prove. The list at the end of the run is where the developer learns of both, so a run nobody reads
to its end hides them.

The words that tell a Session to choose are in the driver's prompt and not in a skill, because
"nobody will answer" is true only in the loop. A developer who runs a skill by hand can still be
asked.

The Plugin's output style tells a Session to offer two options when a person has to decide. The
driver's words pull against it, and no run has yet shown which one wins. The counts the driver keeps
say how many steps ended Blocked, how many Choices were made, and what a Nudge got.

Nothing shows that a Session writes each line when it should. The lines are the Session's own word,
as a review's heading is, and the Suite stays the gate.
