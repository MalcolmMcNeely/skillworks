# A Session arrives in two parts

A read of one Session answers twice. Its events land first and draw the timeline, the figures, the
Findings and the conversation. Its Spans land second and fill in the trace tree, the agent each Step
belongs to and the waits for permission. The answer is Arriving until the second part lands, and the
Session's Depth grows from Thin to Full while a reader looks at it.

ADR 0006 splits a read by day because a long span is many days. One Session is not many days. The
largest Session measured held 2,645 events, well under a single read, and a week of Sessions listed
in 0.08 seconds. The split that matters here is not time but store: the Events store and the Trace
store answer apart, and the Trace store is the slower and the newer of the two.

`Skillworks.Core` joins the two before either part is sent. A tool event finds its span by
`tool_use_id`, a model event finds its span by `request_id`, and the span carries the agent id. The
browser is sent a Session, never a span.

## Considered options

**One whole answer.** Rejected. Nothing would reach the screen until both stores replied, so a slow
or broken Trace store would blank a page that the events alone can nearly fill.

**Day by day, as ADR 0006 reads a span of days.** Rejected. A Session is one thing that a person
reads whole, and cutting it at midnight would split an overnight run into two halves that mean
nothing on their own.

**Join in the browser**, sending events and spans as two plain feeds. Rejected. The join rules are
the hard part, and they rest on beta spans that will change. In `Skillworks.Core` a test holds them
against a real Loki and a real Tempo, the way the other store tests already run. In the browser
nothing could.

## Consequences

A Session with no Spans is Thin, not broken. It opens, it draws, and the parts that need a Span say
so rather than showing a zero. A Finding that rests on a Span reads **not known** in a Thin Session.

A reader who wants only Sessions they can read whole asks the Filter for Full, so the page never
hides a Session without being asked.

This says nothing about following a Session while it runs. A running Session is read back and marked
Running, and live follow is a second transport that needs its own decision.
