namespace Skillworks.Core.Sessions.Steps;

// Claude Code writes an event when a Step ends, so AtUtc is worked back from the length.
public sealed record Step(
    string Id,
    StepKind Kind,
    DateTimeOffset AtUtc,
    long LengthMs,
    string? Tool,
    bool Fault,
    string? Words);
