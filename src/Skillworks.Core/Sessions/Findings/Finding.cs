namespace Skillworks.Core.Sessions.Findings;

// A bar measured and not crossed comes back as no Finding, so a missing Figure means nobody could measure it.
public sealed record Finding(
    FindingKind Kind,
    string? Subject,
    decimal? Figure,
    decimal Bar,
    string? Step,
    DateTimeOffset AtUtc,
    long LengthMs);
