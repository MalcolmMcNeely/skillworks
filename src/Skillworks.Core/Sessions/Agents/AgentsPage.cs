using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Sessions.Agents;

// Only the Steps a Subagent ran: at Full the rest are the main thread's, and at Thin none of them is known.
public sealed record AgentsPage(Depth Depth, IReadOnlyDictionary<string, string> Agents) : ArrivingLine("agents");
