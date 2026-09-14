namespace Skillworks.Core.Activations;

public sealed class Activation
{
    public required string ToolUseId { get; init; }

    public required string SkillName { get; init; }

    public required string SessionId { get; init; }

    // Kept whole: ingest never rereads a line, so a field dropped now costs a full re-read to add back.
    public string? Arguments { get; init; }

    public string? Repository { get; init; }

    public string? GitBranch { get; init; }

    public DateTimeOffset TimestampUtc { get; init; }

    public string? Model { get; init; }

    public string? Effort { get; init; }
}
