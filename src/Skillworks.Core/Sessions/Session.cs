namespace Skillworks.Core.Sessions;

// Length in milliseconds, as a browser measures time that way and every other figure on the wire is a number.
// Friction rides beside Faults and is never added to it, so a reader's own refusals leave a clean run clean.
public sealed record Session(
    string Id,
    DateTimeOffset StartedUtc,
    string? Repository,
    string? Person,
    string Name,
    long LengthMs,
    bool Running,
    int ToolCalls,
    decimal Cost,
    int Faults,
    int Friction);
