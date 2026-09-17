using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Sessions.Agents;

// Only the Steps a Subagent ran: at Full the rest are the main agent's, and at Thin none of them is known.
public sealed record AgentsPage(
    Depth Depth,
    IReadOnlyDictionary<string, string> Agents,
    IReadOnlyList<Subagent> Subagents) : ArrivingLine("agents");
