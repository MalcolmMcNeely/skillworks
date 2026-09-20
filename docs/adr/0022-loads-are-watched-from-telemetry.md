# Loads are watched from telemetry, not a log file

A rule steers the agent, a test enforces part of it, and a skill reads the rest. None of those
readers says which rules a session was actually given. Three switches take rules away, and one of
them, `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, prints nothing at all: no banner, no notice, no line in the
session. A week of work can run with no rules and look exactly like a week with them.

Claude Code emits no telemetry of its own for this. Its log events cover prompts, tools, skills and
api calls, and none of them names an instruction file. So two hooks post the record themselves:
`SessionStart` writes one record for the session, and `InstructionsLoaded` writes one Load per file.
Both go to the Collector already running for Studio, which forwards to Loki.

The pair is what makes the answer readable. `InstructionsLoaded` fires once per file, so a session
that was given nothing fires nothing, and nothing is indistinguishable from a Collector that was
down. A session record with no Loads after it says the rules did not arrive. No records at all says
the Collector was not there. Those stay two different facts.

## Considered options

**A log file.** It was rejected because the records would sit where nothing else can read them, and
joining them to a session would be work done by hand. The hook is handed `session_id` and
`prompt_id`, which are the same values Claude Code puts on every telemetry event as `session.id` and
`prompt.id`, so the join already exists and only a file would throw it away.

**A span in Tempo.** Claude Code puts `TRACEPARENT` in the hook's environment, so a Load could nest
inside the session's own span. It was rejected because there is usually no span yet at session start,
which is the moment the rules load. It would work for every case except the one that matters.

**`InstructionsLoaded` alone.** It was rejected because it cannot report an absence. Zero files
loaded is zero events.

**An alarm rather than a record.** Something that knows which rules it expected and says so when one
is missing. It was deferred, not refused. The expected set is a second truth that can rot, and it
would be guessed before anyone has read a week of real Loads. A record first leaves the alarm
buildable on top.

## Consequences

The hook is written for node. Measured on a developer machine, the whole hook takes about 100 ms
under node and about 750 ms under PowerShell, and PowerShell has to be installed on macOS and Linux.
The event does not block, so neither number reaches the developer, but the setup ships to machines
that are not this one.

A hook that fails says nothing. A bad exit code, and anything written to standard error, reach no
one: only `claude --debug hooks` shows them. The watcher can therefore stop watching in silence, and
nothing here fixes that.

The endpoint is read from `OTEL_EXPORTER_OTLP_ENDPOINT`, which is already set where telemetry is on.
This is for local development. A machine with no Collector is not served, and was not meant to be.
