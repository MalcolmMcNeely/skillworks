# A Child Session names its Parent in a telemetry attribute

The spec loop driver starts every step as its own `claude -p`, so one spec run lands in the Sessions
list as dozens of rows that make no sense apart. The driver is started from the Session that ran
`/spec-loop`, and Claude Code hands that Session's ID to every command it runs as
`CLAUDE_CODE_SESSION_ID`. So the driver passes that ID on to each Session it starts, as
`skillworks.parent.session.id` in `OTEL_RESOURCE_ATTRIBUTES`. Claude Code puts every key from that
variable on every event it sends, so each event of a Child names its Parent, and the list shows the
Parent alone, with its Children's Measures added in.

A Session that names no Parent is never a Child. A chat, a single `/implement`, and a `claude -p`
someone starts by hand keep their own rows.

## Considered options

**A made-up row for the spec.** The driver would tag each Session with the spec number, and the list
would fold them into a row of their own. It was rejected because that row is not a Session: Studio
would have to invent its name, its start, its Cost and its Running state. The Parent is a real
Session, so all of those already exist. The cost is that a driver started by hand from a terminal has
no Parent to name, and its Sessions show one by one, as they did before.

**One shared trace.** A `claude -p` reads `TRACEPARENT` from its environment and puts its spans under
it, so the whole run can be one tree in the Trace store, and its events carry the same `trace_id`.
It was rejected as the link because a trace ID names nothing, and one trace for a run of many hours
grows very large. It does not conflict with the attribute, and a later view of the whole run may
still use it.

## Consequences

The attribute rides every Child event for as long as the Events store keeps it, so renaming it later
leaves old runs split across two names.

The driver adds its key to any `OTEL_RESOURCE_ATTRIBUTES` it was given, and never replaces what is
there. The SessionStart and Load records written by the hook carry the same key, or a Child's own
records would still reach the list without it.

A Child's own commands inherit the variable, so a Session a Child starts names the first Parent too.
The link is one level deep on purpose.
