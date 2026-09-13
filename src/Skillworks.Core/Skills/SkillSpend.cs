using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

/// <summary>
/// What one skill cost. Tokens are split by kind so an expensive skill can be diagnosed rather than
/// merely noticed: a long skill and one that busts the cache look nothing alike here.
/// </summary>
/// <param name="ThinkingTokens">
/// Part of <paramref name="OutputTokens"/> and not on top of it, because that is how it is billed.
/// </param>
/// <param name="CacheWriteTokens">The five minute and the hour added up, though they are priced apart.</param>
/// <param name="Cost">US dollars, worked out from the price table at the moment of the question.</param>
/// <param name="CostIsPartial">
/// True when some of these tokens ran on a model the price table does not name, so the money is a
/// floor and not the answer. Reporting the shortfall as zero is the one lie a cost tool cannot
/// afford.
/// </param>
public sealed record SkillSpend(
    long InputTokens,
    long OutputTokens,
    long ThinkingTokens,
    long CacheReadTokens,
    long CacheWriteTokens,
    decimal Cost,
    bool CostIsPartial)
{
    /// <summary>A skill that fired but made no request of its own.</summary>
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
