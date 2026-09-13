namespace Skillworks.Core.Telemetry;

/// <summary>
/// What a million tokens of each kind costs on one model, in US dollars. Read when a question is
/// asked and never folded into a stored turn, so correcting a price is one row edit rather than a
/// re-read of every transcript on the machine.
/// </summary>
public sealed class ModelPrice
{
    /// <summary>As the transcript spells it, so a row is found without guesswork.</summary>
    public required string Model { get; set; }

    public decimal InputPerMillion { get; set; }

    /// <summary>Thinking is billed here too, so it needs no rate of its own.</summary>
    public decimal OutputPerMillion { get; set; }

    public decimal CacheReadPerMillion { get; set; }

    public decimal CacheWrite5mPerMillion { get; set; }

    public decimal CacheWrite1hPerMillion { get; set; }

    /// <summary>
    /// What these tokens cost at these rates. The thinking is left out on purpose: it is already
    /// inside the output tokens, and charging for it again would double the part that hurts most.
    /// </summary>
    public decimal CostOf(ModelTokens tokens) =>
        (tokens.InputTokens * InputPerMillion +
         tokens.OutputTokens * OutputPerMillion +
         tokens.CacheReadTokens * CacheReadPerMillion +
         tokens.CacheWrite5mTokens * CacheWrite5mPerMillion +
         tokens.CacheWrite1hTokens * CacheWrite1hPerMillion) / 1_000_000m;
}
