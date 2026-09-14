namespace Skillworks.Studio.Api.Tests;

public sealed record SpendRow
{
    public required long InputTokens { get; init; }

    public required long OutputTokens { get; init; }

    public required long ThinkingTokens { get; init; }

    public required long CacheReadTokens { get; init; }

    public required long CacheWriteTokens { get; init; }

    public required decimal Cost { get; init; }

    public required bool CostIsPartial { get; init; }
}
