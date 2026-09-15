namespace Skillworks.Core.Spend;

public sealed class ModelPrice
{
    public required string Model { get; set; }

    public decimal InputPerMillion { get; set; }

    public decimal OutputPerMillion { get; set; }

    public decimal CacheReadPerMillion { get; set; }

    public decimal CacheWrite5mPerMillion { get; set; }

    public decimal CacheWrite1hPerMillion { get; set; }
}
