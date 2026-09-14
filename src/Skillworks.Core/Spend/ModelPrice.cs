namespace Skillworks.Core.Spend;

public sealed class ModelPrice
{
    public required string Model { get; set; }

    public decimal InputPerMillion { get; set; }

    public decimal OutputPerMillion { get; set; }

    public decimal CacheReadPerMillion { get; set; }

    public decimal CacheWrite5mPerMillion { get; set; }

    public decimal CacheWrite1hPerMillion { get; set; }

    // Thinking is left out: it is already inside the output tokens, so adding it would charge it twice.
    public decimal CostOf(ModelTokens tokens) =>
        (tokens.InputTokens * InputPerMillion +
         tokens.OutputTokens * OutputPerMillion +
         tokens.CacheReadTokens * CacheReadPerMillion +
         tokens.CacheWrite5mTokens * CacheWrite5mPerMillion +
         tokens.CacheWrite1hTokens * CacheWrite1hPerMillion) / 1_000_000m;
}
