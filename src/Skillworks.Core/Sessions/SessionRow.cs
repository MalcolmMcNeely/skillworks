namespace Skillworks.Core.Sessions;

// Length in milliseconds, as a browser measures time that way and every other figure on the wire is a number.
// It carries no Measure: each of those arrives on a line of its own, so a slow read costs a reader no rows.
// The last activity is the newest Prompt of the whole piece of work, which is the row's place in the list.
// The days run from the start to the last event of any Child, so a Session opened from the row reads all of it.
public sealed record SessionRow(
    string Id,
    DateTimeOffset StartedUtc,
    string? Repository,
    string? Person,
    string Name,
    long LengthMs,
    bool Running,
    DateTimeOffset LastActivityUtc,
    DateOnly FirstDay,
    DateOnly LastDay);
