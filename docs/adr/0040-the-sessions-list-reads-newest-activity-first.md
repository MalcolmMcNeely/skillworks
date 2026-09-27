# The Sessions list reads newest activity first

The Sessions list starts at now and reads back through Prompts, newest first, fifty rows at a time.
A row's place is the newest Prompt of its piece of work, Parent or any Child. A reader asks for the
next fifty older rows with a button. No span of days narrows the list, and no column sorts it.

ADR 0011 and ADR 0013 read the whole span at once: one total per Session for every read, then sorted
in Studio. Loki answers a total per Session with one series per Session, and refuses a query of more
than 500 series. A week held about 650 Sessions, most of them Children the loop driver starts, and
the reads that group by the words of a Prompt held about 280 series on one busy day. Every gate read
came back refused, so the table stood empty under a Gap at seven days and sometimes at one. What Loki
does fast is read the newest lines of a period with a limit. Fifty rows read that way took about a
second over a week.

A Prompt marks the activity, and not any event, because one busy run writes thousands of events and
Loki would read them all to find each row. A run that works on with no new Prompt keeps its place,
and still reads Running from its last event. The title event was not used, because only one Session
in ten has one.

## Considered options

**Raise Loki's series limit and keep the list.** Rejected. The reads still grow with every Session,
so the list slows as the work grows, and a Loki Studio does not configure keeps the limit.

**Read the Sessions in groups by the first letter of their id.** Rejected. Sixteen reads of the whole
span, four at a time, make the list slower to fix a refusal.

**Keep sorting by a column, over the rows that are loaded.** Rejected. The top Cost of the rows in
hand reads like the top Cost of the week and is not it. The Dashboard answers questions about a whole
period.

**Keep the span of days.** Rejected. Once the list reads newest first, asking for more rows does what
the span did, and two ways to say how far back is one too many.

## Consequences

The Sessions list is the one list no span narrows. A Session opened from it reads the days its own
row covers, where it used to read the table's span.

The rows can change order between two reads, as older work takes a new Prompt.

A reader cannot jump to a date. That comes back as its own change if it is needed.

The midnight rule of ADR 0011 stands: nothing cuts a run at a day boundary.
