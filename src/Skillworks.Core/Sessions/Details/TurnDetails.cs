namespace Skillworks.Core.Sessions.Details;

// SentAs is Claude Code's own value, so a Side request Studio has no name for still says what it was.
public sealed record TurnDetails(
    Purpose Purpose,
    SideRequest? Side,
    string? SentAs,
    string? Model,
    string? Effort,
    string? Speed,
    decimal Cost,
    long LengthMs,
    // Null where Claude Code gave no wait, as an older one sends none and nought would read as an instant start.
    long? FirstWordMs,
    long CacheReadTokens,
    long CacheWriteTokens,
    long InputTokens,
    long OutputTokens,
    string? Words,
    int? WordsLength);
