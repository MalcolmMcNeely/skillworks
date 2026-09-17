namespace Skillworks.Studio.Api.Tests.Sessions.Answers;

public sealed record StepRow
{
    public required string Id { get; init; }

    public required string Kind { get; init; }

    public required DateTimeOffset AtUtc { get; init; }

    public required long LengthMs { get; init; }

    public required string? Tool { get; init; }

    public required bool Fault { get; init; }

    public required string? Words { get; init; }
}
