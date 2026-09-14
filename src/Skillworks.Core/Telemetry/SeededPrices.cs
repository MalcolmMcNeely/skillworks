namespace Skillworks.Core.Telemetry;

// Cache follows the published multipliers of each model's input rate.
internal static class SeededPrices
{
    public static readonly ModelPrice[] All =
    [
        For("claude-opus-5", input: 15m, output: 75m),
        For("claude-sonnet-5", input: 3m, output: 15m),
        For("claude-haiku-4-5", input: 1m, output: 5m),
    ];

    private static ModelPrice For(string model, decimal input, decimal output) => new()
    {
        Model = model,
        InputPerMillion = input,
        OutputPerMillion = output,
        CacheReadPerMillion = input * 0.10m,
        CacheWrite5mPerMillion = input * 1.25m,
        CacheWrite1hPerMillion = input * 2m,
    };
}
