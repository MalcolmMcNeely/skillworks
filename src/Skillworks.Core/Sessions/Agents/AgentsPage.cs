using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Filters;

namespace Skillworks.Core.Sessions.Agents;

// Depth answers for the whole run, and Traced for the Spans alone, so withheld words hide no Span that landed.
public sealed record AgentsPage(
    Depth Depth,
    bool Traced,
    // Only the Steps a Subagent ran, so a Step left out belongs to the main agent wherever Spans landed.
    IReadOnlyDictionary<string, string> Agents,
    IReadOnlyList<Subagent> Subagents) : ArrivingLine("agents");
