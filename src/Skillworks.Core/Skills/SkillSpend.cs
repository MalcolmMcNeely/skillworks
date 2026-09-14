using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

// ThinkingTokens is part of OutputTokens, not on top of it, because that is how it is billed.
public sealed record SkillSpend(
    long InputTokens,
    long OutputTokens,
    long ThinkingTokens,
    long CacheReadTokens,
    long CacheWriteTokens,
    decimal Cost,
    bool CostIsPartial)
{
    public static readonly SkillSpend Nothing = new(0, 0, 0, 0, 0, 0m, false);

    public static SkillSpend Of(
        IReadOnlyList<ModelTokens> tokens,
        IReadOnlyDictionary<string, ModelPrice> prices)
    {
        if (tokens.Count == 0)
        {
            return Nothing;
        }

        var cost = 0m;
        var partial = false;

        foreach (var run in tokens)
        {
            if (prices.TryGetValue(run.Model, out var price))
            {
                cost += price.CostOf(run);
            }
            else
            {
                partial = true;
            }
        }

        return new SkillSpend(
            tokens.Sum(run => run.InputTokens),
            tokens.Sum(run => run.OutputTokens),
            tokens.Sum(run => run.ThinkingTokens),
            tokens.Sum(run => run.CacheReadTokens),
            tokens.Sum(run => run.CacheWrite5mTokens + run.CacheWrite1hTokens),
            cost,
            partial);
    }
}
