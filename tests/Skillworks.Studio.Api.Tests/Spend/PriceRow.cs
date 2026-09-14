namespace Skillworks.Studio.Api.Tests.Spend;

public sealed record PriceRow
{
    public required string Model { get; init; }

    public required decimal InputPerMillion { get; init; }

    public required decimal OutputPerMillion { get; init; }

    public required decimal CacheReadPerMillion { get; init; }

    public required decimal CacheWrite5mPerMillion { get; init; }

    public required decimal CacheWrite1hPerMillion { get; init; }
}
