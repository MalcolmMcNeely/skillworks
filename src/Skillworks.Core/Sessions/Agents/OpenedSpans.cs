using Skillworks.Core.Filters;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Agents;

// A wait for a person and a hook run are told as time here, as a Span never leaves the query that read it.
public sealed record OpenedSpans(
    Depth Depth,
    IReadOnlyDictionary<string, string> Agents,
    IReadOnlyDictionary<string, string> Inside,
    IReadOnlyDictionary<string, AgentRoot> Wrapped,
    IReadOnlyDictionary<string, Stretch> Waited,
    IReadOnlyList<Stretch> Hooked,
    SessionSpans Read);
