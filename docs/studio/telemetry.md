# Studio's telemetry

This page says where Studio's numbers come from, and what the Telemetry switch writes. The
[README](../../README.md) says how to run Studio.

## Where Studio's numbers come from

Studio reads everything it measures from the Events store, a Loki that Claude Code's telemetry
reaches. It never reads the transcripts Claude Code writes to `~/.claude/projects`, and it keeps no
database.

In an organisation, the Events store is the organisation's Loki. Until one exists, the AppHost's
Collector and Loki stand in for it, and Studio shows only what this machine sent.

## What telemetry cannot tell you

A plugin from the organisation's own marketplace is a third-party plugin to Claude Code. Its
Activations arrive with the skill's real name. Its spend does not. On each request made while one of
its skills is in force, Claude Code sends the skill name as `third-party`, and no setting changes
that. Studio shows that spend as one amount, Unnamed spend, and never splits it among skills.

## The Telemetry switch

Claude Code sends nothing until telemetry is on. The Telemetry switch, on the rail of Studio's first
page, turns it on for this machine. Before it acts it says in plain words what will be recorded: what
you type, what Claude Code writes back, what every tool was handed and what it returned, and how long
each step took. Everyone who can read the organisation's stores can read all of it. The switch writes
only when you say so.

It writes these to the `env` block of `~/.claude/settings.json`, all of them or none:

| Variable | Value | What it brings |
|---|---|---|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | `1` | Nothing at all is sent without this one |
| `OTEL_LOGS_EXPORTER` | `otlp` | The events |
| `OTEL_LOG_TOOL_DETAILS` | `1` | A skill's real name, not `custom_skill` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | The Collector, `http://localhost:4318` | |
| `OTEL_METRICS_INCLUDE_REPOSITORY` | `true` | The Repository on every event |
| `OTEL_LOG_USER_PROMPTS` | `1` | What you typed, not `<REDACTED>` |
| `OTEL_LOG_ASSISTANT_RESPONSES` | `1` | What Claude Code answered |
| `OTEL_LOG_TOOL_CONTENT` | `1` | What a tool was handed and returned |
| `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` | `1` | Spans, which are beta |
| `OTEL_TRACES_EXPORTER` | `otlp` | The Spans, to the Trace store |

The switch says telemetry is on only when all eleven hold these values, because a Session recorded
with some of them cannot be read in full. Turning it off puts back what was there before. A Claude
Code session that is already running picks up neither change, so restart it.

The switch writes this machine and no other, and never a repository file. Beside the switch, Studio
shows the `.claude/settings.json` a team would commit to switch everyone on. It is text on a page:
Studio does not commit it, because that decision belongs in review.

The repository variable, `OTEL_METRICS_INCLUDE_REPOSITORY`, reaches past metrics despite its name.
It names the session's `origin` remote on every event, and Studio shows that as a Repository,
`owner/name`. Claude Code 2.1.269 is the first version that sends a Repository. An older Claude
Code, or a session with no `origin` remote, sends none, and Studio shows the Repository as not
recorded.

## What each Session was given

The Plugin's `SessionStart` and `InstructionsLoaded` hooks, in
`plugins/skillworks/hooks/hooks.json`, run `plugins/skillworks/scripts/session-watch.mjs`, so every
repo with the Plugin records its Loads.
`SessionStart` posts one record for each Session, with how it began. `InstructionsLoaded` posts one
Load for each instruction file that reaches it. Both go to `OTEL_EXPORTER_OTLP_ENDPOINT`, and both
carry the Session's `session.id`, so one Loki query reads them beside Claude Code's own events.
With `OTEL_METRICS_INCLUDE_REPOSITORY` on, both also carry the Repository as `vcs.owner.name` and
`vcs.repository.name`, read from the `origin` remote the way Claude Code reads it, so a query
filtered by Repository finds them too. With the switch off, or no `origin` to read, the Repository
is left off and the record still goes. A Session record with no Loads after it says the Rules did
not arrive. No records at all says the Collector was not there.

A hook that fails is silent. Its exit code and its errors reach no one, so the watcher can stop
watching and nothing says so. To see a hook fail, run `claude --debug hooks`.

## Which Session made a commit

Every commit a Session makes names that Session. The Plugin's `PreToolUse` hook runs
`plugins/skillworks/scripts/hooks/session-trailer.mjs`, which adds a `Skillworks-Session: <id>`
trailer to each `git commit` Claude runs through the Bash or PowerShell tool, whether telemetry is on
or off. The spec loop adds one to the commit it makes when it keeps a stopped run's work. The id is
the Session's `session.id`. Read a commit's Sessions back with:

```
git log -1 <commit> --format='%(trailers:key=Skillworks-Session,valueonly)'
```

Take the id to the Stores, or to `claude --resume <id>` on the machine that made the commit.
A commit you make by hand, outside Claude, carries no trailer.
