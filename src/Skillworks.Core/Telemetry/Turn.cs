namespace Skillworks.Core.Telemetry;

/// <summary>
/// One request to the model, and what it spent. The request id is the key because Claude Code
/// writes a transcript record per content block and repeats the whole usage block on each of them,
/// so adding records up would multiply a turn's cost by the number of blocks it happened to hold.
/// </summary>
public sealed class Turn
{
    public required string RequestId { get; init; }

    public required string SessionId { get; init; }

    /// <summary>
    /// The skill in force when the request was made, which is what Attribution means. Null on the
    /// turn that fired a skill, because that one was spent choosing rather than running.
    /// </summary>
    public string? SkillName { get; init; }

    /// <summary>Null when the transcript recorded no working directory.</summary>
    public string? Repository { get; init; }

    public string? GitBranch { get; init; }

    public DateTimeOffset TimestampUtc { get; init; }

    /// <summary>Which prices apply. A model absent from the price table costs an unknown amount.</summary>
    public required string Model { get; init; }

    public string? Effort { get; init; }

    public long InputTokens { get; init; }

    public long OutputTokens { get; init; }

    /// <summary>
    /// Part of <see cref="OutputTokens"/>, not on top of it. Kept apart so a skill that is expensive
    /// because it makes the model think is told from one that is expensive because it writes a lot.
    /// </summary>
    public long ThinkingTokens { get; init; }

    public long CacheReadTokens { get; init; }

    /// <summary>Split from the hour because the two are written at different prices.</summary>
    public long CacheWrite5mTokens { get; init; }

    public long CacheWrite1hTokens { get; init; }
}
