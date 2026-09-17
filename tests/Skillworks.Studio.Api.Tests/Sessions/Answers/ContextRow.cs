namespace Skillworks.Studio.Api.Tests.Sessions.Answers;

public sealed record ContextRow
{
    public required string Id { get; init; }

    public required DateTimeOffset AtUtc { get; init; }

    public required long LengthMs { get; init; }

    public required long Tokens { get; init; }

    public required long WrittenToCache { get; init; }

    public required string? Skill { get; init; }

    public required bool Unnamed { get; init; }

    public required bool Rebuilt { get; init; }
}
