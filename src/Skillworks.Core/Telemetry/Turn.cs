namespace Skillworks.Core.Telemetry;

// Keyed by request id: Claude Code repeats a request's whole usage block on every content block's record.
public sealed class Turn
{
    public required string RequestId { get; init; }

    public required string SessionId { get; init; }

    public string? SkillName { get; init; }

    public string? Repository { get; init; }

    public string? GitBranch { get; init; }

    public DateTimeOffset TimestampUtc { get; init; }

    public required string Model { get; init; }

    public string? Effort { get; init; }

    public long InputTokens { get; init; }

    public long OutputTokens { get; init; }

    // Already inside OutputTokens; kept apart to tell a skill that thinks a lot from one that writes a lot.
    public long ThinkingTokens { get; init; }

    public long CacheReadTokens { get; init; }

    public long CacheWrite5mTokens { get; init; }

    public long CacheWrite1hTokens { get; init; }
}
