namespace Skillworks.Core.Telemetry;

/// <summary>
/// One occasion on which a skill fired, read out of a transcript. The tool use id is the key, so
/// reading the same line twice can never count it twice.
/// </summary>
public sealed class Activation
{
    public required string ToolUseId { get; init; }

    /// <summary>As invoked: <c>&lt;plugin&gt;:&lt;skill&gt;</c> for a skill delivered by a plugin.</summary>
    public required string SkillName { get; init; }

    public required string SessionId { get; init; }

    /// <summary>The leaf of the working directory. Null when the transcript did not record one.</summary>
    public string? Repository { get; init; }

    public string? GitBranch { get; init; }

    public DateTimeOffset TimestampUtc { get; init; }
}
