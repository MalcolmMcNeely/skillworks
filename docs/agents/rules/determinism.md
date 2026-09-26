# Determinism

An agent is non-deterministic by construction. Each section here names one thing that has to come out
the same on a busy machine as on a quiet one, so that a test failing means the code is wrong. Time is
the first section, and today the only one. Ordering, identifiers and culture get sections here when
they are settled.

The YAML block at the end holds the settings the check reads.

## Time

Studio reads one **Clock**. Everything that needs now, a wait or a delay reads it, and it is injected,
so a test can supply its own. `clock` names the type.

- Shipping code reads time, waits and delays through the Clock, and never through the machine's.
- A test never reaches the machine's clock. It holds the Clock still and moves it on purpose.
- A test waits on a fact, never on a duration.
- A Support file may reach the machine's clock, because a poll that waits for a container to be ready
  has to live somewhere. The permission follows from being a Support file, so no list is kept.

### What a good wait looks like

A **Patience** is how long Studio waits on a store before it gives up and reports a Gap. It is built
on the injected Clock, inside the reader that waits, so a busy machine cannot run it out:

```csharp
using var spent = new CancellationTokenSource(patience, clock);
```

A test that needs a Patience to run out waits until the read it holds has been asked for, and then
moves the Clock past the Patience. The wait is on a fact and the move is a decision, so neither is a
race.

### The reaches, and what to write instead

| The reach | What to write |
| --- | --- |
| `DateTime.Now`, `DateTime.UtcNow`, `DateTime.Today`, `DateTimeOffset.Now`, `DateTimeOffset.UtcNow` | `clock.GetUtcNow()` |
| `Stopwatch`, `Environment.TickCount`, `Environment.TickCount64` | `clock.GetTimestamp()`, then `clock.GetElapsedTime(from)` |
| `Thread.Sleep`, `Task.Delay` | Wait on a fact. Where a delay is the fact, `clock.Delay(span)` |
| `new Timer(...)`, `new PeriodicTimer(period)` | `clock.CreateTimer(...)`, or `new PeriodicTimer(period, clock)` |
| `new CancellationTokenSource(delay)`, `CancelAfter(...)` | `new CancellationTokenSource(delay, clock)` |
| `client.Timeout = span`, `new HttpClient { Timeout = span }` | A Patience on the Clock, in the reader that waits |

The real Clock is judged by where it sits. Handing it to a registration, as the default a Harness
replaces, is the whole of the permission. Naming it anywhere else is a reach:

```csharp
services.TryAddSingleton(TimeProvider.System);
TimeProvider clock = TimeProvider.System;
```

The first line hands the Clock over, and a Harness replaces what it registered. The second binds it
to a name, and every read through that name is past the seam a test controls.

### Fakes

A fake is used where the real thing cannot be made to misbehave, or where it forces a race, and not
otherwise. Real store containers stay: the queries, the day-by-day windowing and the answer parsing
are proved against them, and that is the code most likely to be wrong.

Where an interface needs faking, `NSubstitute` is the default, so the next agent does not pick a
different one. The stand-ins written by hand stay that way. They stand in for a store that is down,
failing or never answers, which a running container cannot be made to be.

## What the check reads

`contexts` names the contexts, from `CONTEXT-MAP.md`, whose C# this rule judges. A context joins the
list the day its code can pass, because a rule switched on before the code can meet it leaves the
suite red on purpose. Studio is on the list because it reads a Clock. Architecture is on the list
because it reads none, and the rule is what keeps that true. A name no context in the map carries
is a breach, so the list cannot go stale and quietly judge nothing.

The check reads C# as code and never as text, so a file named for a reach, and a reach written inside
a string, are both left alone. The front end is held to the same rule by its own linter.

```yaml
clock: TimeProvider
contexts:
  - studio
  - architecture
```
