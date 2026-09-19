namespace Skillworks.Studio.Api.Tests.Watch.Skills;

public sealed record OriginRow
{
    public required string? Trigger { get; init; }

    public required string? Source { get; init; }

    public required string? Plugin { get; init; }

    public required string? Marketplace { get; init; }
}
