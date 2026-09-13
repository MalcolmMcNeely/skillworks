namespace Skillworks.Core.Telemetry;

/// <summary>
/// One occasion on which a skill fired, read out of a transcript. The tool use id is the key, so
/// reading the same line twice can never count it twice.
/// </summary>
public sealed class Activation
{
    public required string ToolUseId { get; init; }

    public required string SkillName { get; init; }

    public required string SessionId { get; init; }

    /// <summary>
    /// What the skill was called with, kept as the transcript wrote it: the whole Skill block's
    /// input, JSON and all. Stored whole rather than picked apart, because ingest never revisits a
    /// line it has read and a field dropped now costs a full re-read to add back. Null on a firing
    /// read before Studio kept this, which a full re-ingest fills in.
    /// </summary>
    public string? Arguments { get; init; }

    /// <summary>Null when the transcript recorded no working directory.</summary>
    public string? Repository { get; init; }

    public string? GitBranch { get; init; }

    public DateTimeOffset TimestampUtc { get; init; }

    /// <summary>What chose the skill, so a firing is compared with one made on the same terms.</summary>
    public string? Model { get; init; }

    public string? Effort { get; init; }
}
