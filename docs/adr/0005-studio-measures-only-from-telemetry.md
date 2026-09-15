# Studio measures only from telemetry, in the organisation's Loki

This supersedes ADR 0002. Studio no longer reads Transcripts. In an organisation every developer
has their own machine, so a Transcript on one laptop tells Studio nothing about the rest, and only
what reaches a central store can be measured. Everything Studio shows now comes from Claude Code's
OpenTelemetry events in Loki, and Studio keeps no database of its own. Loki's address is
configuration; the AppHost's Collector and Loki stand in for the organisation's until real
resources exist.

The events carry almost everything the Transcripts did
([monitoring docs](https://code.claude.com/docs/en/monitoring-usage)). `skill_activated` names the
skill, its trigger, source, plugin and marketplace once `OTEL_LOG_TOOL_DETAILS=1` is set.
`api_request` carries one request's model, effort, tokens by kind, `request_id`, `cost_usd` and the
skill in force. From Claude Code 2.1.269, `OTEL_METRICS_INCLUDE_REPOSITORY=true` puts `vcs.*`
repository attributes on every event.

## What was given up

- **Branch.** No skill or request event carries it.
- **Thinking tokens and the 5-minute and 1-hour cache write split.** Telemetry reports neither.
- **Arguments.** They are only in a `tool_result` or, for a typed skill, in prompt text that is
  redacted unless every developer's prompts are sent to the store.
- **Per-skill spend for a plugin from a private marketplace.** `skill.name` on `api_request` is the
  literal `third-party` for such a plugin, and no setting lifts it. The catalogue is one, so its
  spend arrives unnamed.
- **Faults and local history.** Nothing reports a lost event, and nothing sent before telemetry was
  switched on is ever seen.

## Considered options

**Price each Turn with Studio's own Price table.** Rejected. Telemetry's `cost_usd` is an estimate,
but an organisation sets its contracted prices once through the `modelPricing` managed setting, and
a Studio table would be one developer's opinion of the price. Telemetry also lacks the token kinds
the table priced and spells the model differently, and the table was the last thing in SQLite.

**Credit `third-party` spend to the latest plugin skill activated in the same session.** Rejected.
Nested skills and parallel subagents can each have a different plugin skill in force, nothing in the
event says which, and with the Transcripts gone nothing could check the guess. Unnamed spend is
shown as its own amount.

**Prometheus for spend.** Rejected. The cost and token metrics carry the same redaction as the
events, with no request or prompt id, as 60-second deltas. Loki's aggregate queries give the same
totals from the events.

## Consequences

Totals come from LogQL aggregate queries, so a busy organisation never cuts them short, and only a
list of individual events can hit the read cap. A Filter span longer than Loki's query limit is
split into several queries.

An Activation shows only what `skill_activated` says. Studio never joins events to fill in a field
an event does not carry.

Tests run against a real Loki in a container, because the queries are where the logic now lives.
