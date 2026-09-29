namespace Skillworks.Core.Sessions.Details;

// SentAs is Claude Code's own value, so a Side request Studio has no name for still says what it was.
public sealed record TurnDetails(
    Purpose Purpose,
    SideRequest? Side,
    string? SentAs,
    long OutputTokens,
    decimal Cost);
