namespace Skillworks.Core.Sessions.Context;

// Skill is null both where none was in force and where Claude Code would not name one, so Unnamed tells them apart.
public sealed record ContextPoint(
    string Id,
    DateTimeOffset AtUtc,
    long LengthMs,
    long Tokens,
    long WrittenToCache,
    string? Skill,
    bool Unnamed,
    bool Rebuilt);
