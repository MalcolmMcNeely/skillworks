# Telemetry has two stores: SQLite for transcripts, Loki for events

Studio reads skill usage from two places, and a future reader will ask why one was not enough.

**Transcripts into SQLite.** Every assistant record in `~/.claude/projects/**/*.jsonl` carries
`attributionSkill` — the real skill name — beside the full `usage` block: input, output, cache read,
cache write, thinking tokens, model, effort and speed. Cost per skill is therefore already on disk
and needs nothing switched on. This machine holds 678 MB across 1471 files, far too much to reparse
per request, so a background job parses it once into SQLite and keeps up with new sessions.
Transcripts are also the durable record: they exist whether or not Studio is running.

**Events into Loki.** Transcripts do not say where a skill came from. The `skill_activated` log
event does, carrying `skill.source`, `plugin.name` and `marketplace.name`, and that provenance is
what tells an engine from an entry point once the catalogue ships as a plugin. Claude Code sends
OTLP to an OpenTelemetry Collector, which forwards to Loki; `Skillworks.Core` queries Loki's
`/loki/api/v1/query_range` over `HttpClient`. Both containers are Aspire resources with
`WithPersistentLifetime()` and a data volume, so they keep catching events after the AppHost stops.

## Consequences

The two stores join on skill name and time, in C#, not in a database. That is the cost of the
split, and it is the reason a single store was the tempting alternative.

The Collector adds a hop that only forwards today. It is there for the seam: dropping noisy events,
renaming fields, and fanning out to a second sink later are all collector config, invisible to
Claude Code and to Studio.

Grafana is not part of this. Studio is the dashboard, and a second UI over the same data is waste.
The three hand-started `claude-loki`, `claude-grafana` and `claude-renderer` containers predate this
decision and must be removed — Aspire's Loki wants port 3100, which the old one holds.

Nothing is emitted until `~/.claude/settings.json` carries the `OTEL_*` variables, so Studio writes
that block itself, merging rather than replacing and asking before the first write. The collector's
host port is pinned so the value stays stable across runs.
