# Studio reads one Clock, and a test holds it still

The **Harness** entry has said since it was written that a test stands Studio up on a clock that does
not move. It moved. Three stores set `client.Timeout`, which `HttpClient` measures on the machine's
clock whatever Clock is injected, so the test Clock had to run at real speed for a wait to end at
all. That left the answer to "did this read fall short?" in the hands of whatever else the machine
was doing, and tests failed a different one each run under load.

So Studio reads one Clock. Everything that needs now, a wait or a delay reads it, and a test holds it
still and moves it on purpose. A **Patience** is measured on the Clock, in the reader that waits, the
way the trace store's whole-read wait already was. `.claude/rules/determinism.md` writes this down and
a check holds the code to it: the C# half in `Skillworks.Architecture`, which already parses C# and so
never matches a file name or a string; the TypeScript half in the front end's own linter, beside the
module boundaries it already holds. A reach for the machine's clock is a breach in code that ships and
in a test, and allowed in a Support file, where a poll that waits for a container to be ready has to
live.

The rules file is named for determinism and not for time. Time is all it holds today. An agent is
non-deterministic by construction, and steering it away from non-determinism is a standing need, so
ordering, identifiers and culture get sections in this file when they are settled rather than files of
their own.

## Considered options

**Write the rule and leave the code alone.** Rejected. `client.Timeout` cannot be reached by a test at
all, so the rule would have forbidden the only thing the code made possible, and the flaky tests would
have stayed flaky. A rule an agent cannot follow teaches it that rules are optional.

**Fake the stores and drop the containers.** Rejected. Real Loki and real Tempo are where the queries,
the day-by-day windowing and the answer parsing are proved, and that is the code most likely to be
wrong. Most tests are deterministic against a real container and gain from it. A fake belongs only
where the real thing cannot be made to misbehave, or where it forces a race.

**Rewrite the four stand-ins with a faking library.** Rejected. They stand in for a store that is down,
failing or never answers, which a running container cannot be made to be, so they are already the right
answer. `HttpMessageHandler.SendAsync` is `protected`, which is the one shape a faking library handles
worst — reaching it needs the subclass we already have. A faking library is the default when an
interface needs faking, and nothing here does.

**Write the still Clock ourselves.** Rejected. Holding time still means overriding `CreateTimer` as
well as `GetUtcNow`, because a cancellation built on a Clock fires through its timer. A queue of
pending timers fired in order is a concurrency primitive, not harness glue, and the kind of thing that
is subtly wrong for a year. Microsoft ships one.

**Keep the word Timeout for the wait.** Rejected. The rule forbids `client.Timeout`. A glossary that
also said Studio has a Timeout would put the banned line one keystroke from the word an agent had just
looked up. **Patience** cannot be mistaken for a member on `HttpClient`.

**One check that reads both languages as text.** Rejected. Two lines in this repository are C# written
inside a string — sample code in a temporary tree and a fixture file name — and a text scan reports
both. Each language is held by the tool that parses it, which is the shape the front end's module
boundaries already use.

## Consequences

A check cannot catch a test that races by construction, and the trace store's own tests did: they used
a real delay to outlast a wait measured on the Clock. Holding time still fixes those better than any
rule would. A real delay can never outlast a still Clock, so such a test stops flaking and starts
failing every run until someone makes it move the Clock on purpose. A race becomes a broken test.

The front end gains a Clock of its own, supplied the way the C# one is, because two components tick a
now-marker and two routes read today. No front-end test renders them yet. The first one written would
have flaked, and now cannot.
