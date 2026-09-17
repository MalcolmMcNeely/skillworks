# The Sessions list answers as one page

A read of the Sessions list sends its head, then every row in one line, then its end. It keeps the
NDJSON transport, the Arriving state and the Gap that ADR 0006 gave every Events store read, and it
drops the one thing ADR 0006 asked for: the day-by-day split.

ADR 0006 splits a read by day because a span of days is many days. The Sessions list is not a span of
days on screen. It is a list of runs, and a run is not a day: a Session that began at half past eleven
one night and ended after midnight belongs to no single day. Cutting it at the day boundary would
give two half-rows, each with the wrong start and the wrong length, and nothing on the screen could
put them back together. ADR 0010 rejected the same split for the same reason, for one Session.

The measurement that bought ADR 0006 does not apply here either. Its worry was twelve aggregate
queries a day over a month. The list asks four aggregate queries for the whole span, and a week of
Sessions at one developer's volume came back in 0.08 seconds.

## Considered options

**Day by day, as ADR 0006 reads a span of days.** Rejected, because of the midnight cut above.

**A row at a time.** Rejected. The rows are known together, from four totals over the whole span, so
sending them one at a time would only add lines to the answer without putting anything on screen
sooner.

**One plain JSON answer, outside the Arriving transport.** Rejected. The screen still needs to know
whether the answer fell short, and the Gap, the signal word and the Arriving state already carry
that. A second shape for the same question would be two things to read.

## Consequences

A store that stops answering part way leaves no rows at all, where a day-by-day read would keep the
days that landed. The answer carries an unreachable Gap naming every day of the span. This is the
cost of the midnight rule, and it is paid only by this list.

An answer that has fallen short is told apart from one that found nothing by the row line itself:
where it is absent the screen is still reading, and where it carries no rows the period was quiet.

The list's queries grow with the number of Sessions and the number of Prompts in the span, not with
the number of events, so a busy run never cuts it short. How they behave at many developers' volume
is not measured, and is the same open question the two stores' retention already is.

## Correction, 2026-09-17

"The list asks four aggregate queries for the whole span" was true when this was written and is not
true now. The list asks nine, and up to eleven with a Repository or a Skill filter, and a tenth goes
to the Trace store when a reader narrows by Depth. The 0.08 second week was measured against the
four-query list.

ADR 0013 replaces the one-page answer with a gate and its Measures. The midnight rule this ADR
records is not replaced, and ADR 0013 rests on it.
