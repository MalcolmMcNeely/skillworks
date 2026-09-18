# The Sessions list sends its rows before its Measures

A read of the Sessions list sends its head, then its rows as soon as the reads that decide which runs
exist have landed, then each Measure on its own as it lands, then its end. ADR 0011 gave this list
one page of rows. It now has a gate, and the Measures arrive behind it.

ADR 0011 costed the list at four aggregate queries over the whole span. It asks nine, and up to
eleven: a Repository filter adds the unnarrowed survey, a Skill filter adds the activation read, and
a Depth filter sends a tenth to the Trace store. Nine span-wide queries against a Loki that runs four
at a time is the shape ADR 0006 measured at 13 to 15 seconds on a month, and every one of them had to
land before a single row could be drawn, because `Readings.Unreachable` ORs all nine. One store read
that timed out emptied the whole table.

Five reads decide which runs exist and what they are called: the run list, the first event, the last
event, the title and the first prompt. They are the gate, and they are issued ahead of the rest. A
Skill filter puts the activation read in the gate and a Depth filter puts the Trace store read there,
because both decide which rows exist. A reader who arrives already sorted by a Measure puts that
Measure's reads in the gate, so rows are never drawn in one order and then moved into another.

Behind the gate come the Measures: Tool calls from the tool result read, Cost from the turn read,
Faults from the tool result read and the model error read together, and Friction from the decision
read. No column draws Friction today, and it rides the answer because its read is already paid for.

The midnight rule of ADR 0011 stands. Nothing here cuts a run at a day boundary.

## Considered options

**Day by day, as ADR 0006 reads a span of days.** Rejected again, for the reason ADR 0011 gave. A run
that began before midnight would arrive twice, and a row's start and length would grow as older days
landed, so the table would sort itself again under the reader's hand.

**A gate of three reads**, leaving the name to arrive behind it. Rejected. The gate would cost one
Loki round instead of two, but the name is how a reader finds the run they want, and a name that
changes under the cursor is worse than one more round. The fifth read rides the second round beside
the Measure reads anyway.

**One line per read.** Rejected. Faults is the tool faults of one read plus the model faults of
another, so a reader would watch the number climb and have no way to know which of the two it had
reached. The answer speaks Measures, and a Measure lands whole.

**A fixed order for the Measures.** Rejected. It would have the API hold finished work back to buy an
order a test could read top to bottom. The Measure reads go out together, so a test asserts which
lines came instead.

**Sorting while the answer arrives.** Rejected. A reader who sorted on a Measure that had not landed
would watch the table settle twice. The column headings are inert until the answer is complete, and
the heading over a Measure that fell short stays inert after.

## Consequences

One slow read no longer empties the table. Where a Measure falls short the rows stand, its cells read
a dash, and the answer's Gap names the Measures it could not read. Where a gate read falls short
there are no rows to stand, so the table is empty with a Gap, as before.

A cell whose Measure has not landed is blank and carries the Arriving state the Map and the rail
already use, so no new word and no new symbol reaches the screen.

The whole-table wait shrinks to the gate. What the table says while it waits covers five reads, not
nine.

Nothing retries by itself, as ADR 0006 already said. A Measure that fell short comes back when the
reader changes the Filter.

The glossary gains **Measure** and puts **Figure** under _Avoid_, but the code still spells it
`Figure` in a Finding, a folder and a class name. Figure joins the banned words when that rename
lands, and not before, because the check reads whole files.

This says nothing about the Session page, which ADR 0010 already splits by store, or about following
a run while it happens.

## Correction, 2026-09-18

"A Depth filter puts the Trace store read there, because both decide which rows exist" no longer
holds, and neither does the half of the consequence that rests on it. The Trace store read has left
the gate. Where it falls short the rows stand, un-narrowed, and the answer's Gap says the table was
not narrowed by a Depth it could not read.

The reason is that the two gate reads are not alike. The activation read and the five that name a run
come from the Events store, and a run they leave out is a run that did not happen. The Trace store
answers apart from the Events store and falls short apart from it, so a Depth it could not read says
nothing about which runs exist. Emptying the table on it spent the whole Events store answer on a
second store's outage, and a reader who asked for Full Sessions got a blank page where the rows were
already in hand.

Narrowing on half an answer is still refused. A run the store left out would go missing from the
table without a word, so a shortened Depth read narrows nothing either, and its Gap says so.

The rest of this ADR stands. The gate is now the five reads that name a run, plus the activation read
under a Skill filter, plus the reads behind a Measure a reader sorted on. Where one of those falls
short there are still no rows to stand.
