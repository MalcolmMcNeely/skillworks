namespace Skillworks.Studio.Api.Tests.Watch.Skills;

public sealed record TurnTotalsRow
{
    public required long InputTokens { get; init; }

    public required long OutputTokens { get; init; }

    public required long CacheReadTokens { get; init; }

    public required long CacheCreationTokens { get; init; }

    public required decimal Cost { get; init; }
}
