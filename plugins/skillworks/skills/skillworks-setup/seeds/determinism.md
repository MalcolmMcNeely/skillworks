# Determinism

An agent is non-deterministic by construction. Each section here names one thing that has to come out
the same on a busy machine as on a quiet one, so that a test failing means the code is wrong. Time is
the first section, and Order of events the second. The order of items, identifiers and culture get
sections here when they are settled.

The YAML block at the end holds the settings a check reads, once the team adds one.

## Time

The code reads one **Clock**. Everything that needs now, a wait or a delay reads it, and it is
injected, so a test can supply its own. `clock` names the type.

- Shipping code reads time, waits and delays through the Clock, and never through the machine's.
- A test never reaches the machine's clock. It holds the Clock still and moves it on purpose.
- A test waits on a fact, never on a duration. Order of events, below, says what a wait before an act
  waits on.
- A support file may reach the machine's clock, because a poll that waits for a container to be ready
  has to live somewhere. The permission follows from being a support file, so no list is kept.

### What a good wait looks like

A wait on a slow dependency is built on the injected Clock, inside the code that waits, so a busy
machine cannot run it out:

```csharp
using var spent = new CancellationTokenSource(patience, clock);
```

### The reaches, and what to write instead

| The reach | What to write |
| --- | --- |
| `DateTime.Now`, `DateTime.UtcNow`, `DateTime.Today`, `DateTimeOffset.Now`, `DateTimeOffset.UtcNow` | `clock.GetUtcNow()` |
| `Stopwatch`, `Environment.TickCount`, `Environment.TickCount64` | `clock.GetTimestamp()`, then `clock.GetElapsedTime(from)` |
| `Thread.Sleep`, `Task.Delay` | Wait on a fact. Where a delay is the fact, `clock.Delay(span)` |
| `new Timer(...)`, `new PeriodicTimer(period)` | `clock.CreateTimer(...)`, or `new PeriodicTimer(period, clock)` |
| `new CancellationTokenSource(delay)`, `CancelAfter(...)` | `new CancellationTokenSource(delay, clock)` |
| `client.Timeout = span`, `new HttpClient { Timeout = span }` | A wait on the Clock, in the code that waits |

The real Clock is judged by where it sits. Handing it to a registration, as the default a test host
replaces, is the whole of the permission. Naming it anywhere else is a reach:

```csharp
services.TryAddSingleton(TimeProvider.System);
TimeProvider clock = TimeProvider.System;
```

The first line hands the Clock over, and a test host replaces what it registered. The second binds it
to a name, and every read through that name is past the seam a test controls.

## Order of events

A test that acts while the code runs first waits on a fact that shows the code is where the act needs
it. An act is anything a test does to the code while it runs: a close of a request, a cancel, a Clock
move, a second request, a stop of a test host. The rule covers every act, and not only these.

- A fact is something the test sees at the point the act needs, and it comes from the test host or a
  stand-in, which is a fake the test writes by hand. The stand-in saying that it holds a call is one.
- The code's own order is not a fact. A line the code writes after it starts some work does not show
  that the work reached the stand-in. A line from the code counts only when the line is itself the
  state the act needs. Shipping code can change its own order for a good reason, and a comment in a
  test cannot stop it.
- Where the test host has no fact at the point an act needs, the test adds one to the stand-in.
  The testing rule, `docs/agents/rules/testing.md`, already allows a stand-in where the real thing
  forces a race.

No check reads this section, so a green suite does not prove it. A race has no name a check can find.
The `standards` review judges each change by it.

### What a good act looks like

A test that needs a wait to run out waits until the call it holds has been made, and then moves the
Clock past the wait. The wait is on a fact and the move is a decision, so neither is a race.

A test that closes a request while a stand-in holds a call waits until the stand-in reports that it
holds the call, and closes the request only after that. A call the code has not made when its
request closes may never be made, so a close that comes first leaves the stand-in nothing to hold,
and a wait for it to let go never ends.

## What a check reads

Both settings are enforced only once a check exists that reads them: `clock` and `contexts`. Until
then, an agent reads them as prose. `/skillworks:architecture-tests` adds the check.

`contexts` names the contexts, from `CONTEXT-MAP.md`, whose code this rule judges. A context joins the
list the day its code can pass, because a rule switched on before the code can meet it leaves the
suite red on purpose. A name no context in the map carries is a breach, so the list cannot go stale
and quietly judge nothing.

A check should read code as code and never as text, so that a file named for a reach, and a reach
written inside a string, are both left alone.

```yaml
clock: TimeProvider
contexts: []
```
