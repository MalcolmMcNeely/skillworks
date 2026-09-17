namespace Skillworks.Core.Sessions.Agents;

// Only the opening words of a brief were ever recorded, so Brief is the whole of what a reader can get.
public sealed record Subagent(
    string Id,
    string Name,
    string? Type,
    DateTimeOffset AtUtc,
    long LengthMs,
    int ToolCalls,
    decimal Cost,
    int Faults,
    string? Brief,
    string? Report);
