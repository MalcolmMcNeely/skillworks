# Answers from the Events store arrive day by day

Every read Studio makes from the Events store streams its answer back one day at a time, newest day
first, as one JSON object per line (NDJSON) over `fetch`. The screen shows each day as it lands, so
an answer is Arriving until its last day lands and complete after that. Studio has this one way to
load. Health, the telemetry switch and the catalogue read the machine Studio runs on, so they stay
plain answers.

The reason is a month of realistic volume. A 30-day skills table asks Loki 12 aggregate queries, each
about a second over 30 days. Loki runs 4 at a time, so the screen stayed empty for 13 to 15 seconds
and passed the API's 5 second Loki timeout. The same 12 queries over the newest single day come back
in about half a second, and 30 one-day queries cost about the same in total as one 30-day query. A
day-by-day answer puts figures on screen within a second whatever the span, without making the
whole answer slower.

## Considered options

**Make the queries faster first.** Not chosen. Daily buckets were three times faster on a test Loki
split by 24 hours, but the AppHost's Loki splits by 1 hour and was not measured. A faster total still
grows with the span, and a longer span or a busier organisation brings the empty screen back. Speed
stays open as separate work.

**One figure at a time.** Rejected. Counts would land before cost, so for a while the figures on
screen would cover different things, and the first figure still waits longer as the span grows.

**One request per day from the browser.** Rejected. A month is 30 requests, and the browser would
have to order the days and decide what a failure means. The server decides both in one place.

**Server-sent events.** Rejected. `EventSource` only sends GET, cannot take the abort signal every
read already uses, and reconnects on its own, so a store that stops answering would be retried
behind the developer's back.

## Consequences

A store that stops answering part way keeps the days that landed. The answer ends complete with an
unreachable Gap that names the days it could not read. Nothing retries by itself.

A screen reads one answer, so it has one Arriving state. The skills table carries each day's counts
by skill, by trigger and by hour, and the latest firing. No screen reads a list of individual
events, so the activation list and its pages were deleted, and no answer can hit the read cap.

Changing the Filter stops the answer that is arriving.

The treemap on the at-a-glance screen lays itself out again as each day lands, with tiles sliding into
place. They move at once when reduced motion is set.
