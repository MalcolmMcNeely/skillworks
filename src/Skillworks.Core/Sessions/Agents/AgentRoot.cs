namespace Skillworks.Core.Sessions.Agents;

// The stretch a Subagent ran for, read off the Span that wraps its whole run, so no Span leaves the join.
public sealed record AgentRoot(string ToolUse, DateTimeOffset Started, DateTimeOffset Ended);
