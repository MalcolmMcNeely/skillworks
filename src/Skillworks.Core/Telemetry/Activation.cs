namespace Skillworks.Core.Telemetry;

/// <summary>
/// One occasion on which a skill fired, read out of a transcript. The tool use id is the key, so
/// reading the same line twice can never count it twice.
/// </summary>
public sealed class Activation
{
    public required string ToolUseId { get; init; }

    public required string SkillName { get; init; }

    /// <summary>
    /// Kept even though nothing reads it yet. Ingest never revisits a line it has read, so a field
    /// dropped now costs a full re-read of the transcripts to add back.
    /// </summary>
    public required string SessionId { get; init; }

    /// <summary>Null when the transcript recorded no working directory.</summary>
    public string? Repository { get; init; }

    public string? GitBranch { get; init; }

    public DateTimeOffset TimestampUtc { get; init; }
}
