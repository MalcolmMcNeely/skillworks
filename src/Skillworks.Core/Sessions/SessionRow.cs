namespace Skillworks.Core.Sessions;

// Length in milliseconds, as a browser measures time that way and every other figure on the wire is a number.
// It carries no Measure: each of those arrives on a line of its own, so a slow read costs a reader no rows.
public sealed record SessionRow(
    string Id,
    DateTimeOffset StartedUtc,
    string? Repository,
    string? Person,
    string Name,
    long LengthMs,
    bool Running);
