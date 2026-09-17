using Skillworks.Core.Filters;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Agents;

public sealed record OpenedSpans(
    Depth Depth,
    IReadOnlyDictionary<string, string> Agents,
    IReadOnlyDictionary<string, string> Inside,
    IReadOnlyDictionary<string, AgentRoot> Wrapped,
    SessionSpans Read);
