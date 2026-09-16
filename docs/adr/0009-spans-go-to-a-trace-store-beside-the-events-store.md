# Spans go to a Trace store beside the Events store

This supersedes the part of ADR 0005 that says Studio measures only from the organisation's Loki.
Claude Code's spans now go to a Grafana Tempo, and Studio reads both stores. The Collector grows a
traces pipeline beside its logs pipeline, and Tempo becomes a persistent Aspire container like Loki.
The glossary gains **Trace store**, because a trace is not an event and the two stores fall short
apart from each other.

The reason is a session view. Three things a reader needs are on a span and on nothing else.

**Which agent ran a step.** No log event carries an agent id. A run of two `general-purpose`
subagents at once was measured: every event from both carried the same `query_source`, the same
`agent_name` and the same `prompt_id`, with no way to tell them apart. Seven days of real data held
238 such overlaps, because a three-agent review fires three at once. On spans the two agents carried
distinct ids, every span inside each subagent carried its own agent's id, and the partition was
clean.

**What a step contained.** A span nests. `claude_code.tool.execution` under an Agent call is the
whole subtree of one subagent, holding its own model calls and its own tool calls. Events carry no
such link, so a subagent's tool calls mix into the parent.

**How long a person took to answer.** `claude_code.tool.blocked_on_user` is the wait for permission.
Without it a tool bar is one solid block, and the time a person spent not pressing a key reads as
work.

The join costs nothing. Every log event that matters carries `trace_id` and `span_id`, and a tool
event finds its span by `tool_use_id` while a model event finds its span by `request_id`. Both paths
were measured end to end.

## What spans do not carry

No span carries text. The `tool.output` span event does not fire on an Agent call at all, so neither
the instruction sent to a subagent nor its report is on a span. The report is recoverable, uncut,
from the subagent's own `assistant_response` event. The instruction is not: only its opening words
survive, with the true length beside them. A reader gets the description its caller wrote, which
names what the subagent was for.

## Considered options

**Events alone.** Rejected. It cannot tell two subagents of one type apart, it cannot say who ran a
tool call, and it has no permission wait, so "where the time went" would count a subagent's work as
the main thread's.

**Read the task output files on the developer's machine** for the full instruction and report.
Rejected. Studio reads the organisation's stores and never the machine it runs on, so one laptop's
files say nothing about anybody else.

**Raw API bodies.** Rejected for now. It would close the instruction gap and carry every turn
untruncated, but it is a much larger recording, the switch is undocumented, and its file mode points
at the developer's disk. It stays open if the missing instruction turns out to matter.

**One store, with Tempo inside the Events store term.** Rejected. The word says events, the two
containers speak different query languages, and they fail on their own. Depth, which says whether a
Session can be read in full, only means something if spans can be absent while events are there.

## Consequences

Health gains a Lamp. The Events store and the Trace store start, work, switch off and break apart
from each other, and a Gap names which of them fell short.

Every developer must switch traces on, beside the content settings, or their Sessions read Thin.
Studio's telemetry switch writes all of it as one act, for the machine it runs on and no other.

Spans are beta. Their names and attributes can change under us, so the join rules live in
`Skillworks.Core` where a test can hold them to a real Tempo.
