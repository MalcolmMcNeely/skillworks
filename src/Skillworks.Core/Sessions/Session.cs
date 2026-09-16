namespace Skillworks.Core.Sessions;

// Length in milliseconds, as a browser measures time that way and every other figure on the wire is a number.
public sealed record Session(
    string Id,
    DateTimeOffset StartedUtc,
    string? Repository,
    string? Person,
    string Name,
    long LengthMs,
    bool Running);
