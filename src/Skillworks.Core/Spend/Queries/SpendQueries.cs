using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Spend.Queries;

public sealed class SpendQueries(EventsStoreReader events)
{
    private const string EventName = "api_request";

    // Sent in place of any skill from a plugin outside Anthropic's marketplaces, so it names no one skill.
    private const string Unnamed = "third-party";

    private const string CostAttribute = "cost_usd";

    private const string InputAttribute = "input_tokens";

    private const string OutputAttribute = "output_tokens";

    private const string CacheReadAttribute = "cache_read_tokens";

    private const string CacheCreationAttribute = "cache_creation_tokens";

    private const string ModelAttribute = "model";

    private const string EffortAttribute = "effort";

    private static readonly string[] BySkillName = [EventAttributes.Skill];

    // One query per attribute: Loki unwraps one at a time, and every pairing multiplies the series.
    public async Task<SpendTally> TallyBySkillAsync(DaySpan span, Filter filter, CancellationToken cancellationToken)
    {
        var turns = Turns(span) with { Repository = filter.Repository, Skill = filter.Skill };

        Task<EventTotals> Sum(string attribute) => events.SumAsync(turns, attribute, BySkillName, cancellationToken);

        Task<EventTotals> CountBy(string attribute) => events.CountAsync(turns, [EventAttributes.Skill, attribute], cancellationToken);

        var costSum = Sum(CostAttribute);
        var inputSum = Sum(InputAttribute);
        var outputSum = Sum(OutputAttribute);
        var cacheReadSum = Sum(CacheReadAttribute);
        var cacheCreationSum = Sum(CacheCreationAttribute);
        var modelCount = CountBy(ModelAttribute);
        var effortCount = CountBy(EffortAttribute);
        var surveying = events.CountAsync(Turns(span), [], cancellationToken);

        var (cost, input, output, cacheRead, cacheCreation, model, effort, period) = (
            await costSum,
            await inputSum,
            await outputSum,
            await cacheReadSum,
            await cacheCreationSum,
            await modelCount,
            await effortCount,
            await surveying);

        var costs = PerSkill(cost);
        var inputs = PerSkill(input);
        var outputs = PerSkill(output);
        var cacheReads = PerSkill(cacheRead);
        var cacheCreations = PerSkill(cacheCreation);
        var models = Names(model, ModelAttribute);

        TurnTotals SpendOf(string skill) => new(
            (long)inputs.GetValueOrDefault(skill),
            (long)outputs.GetValueOrDefault(skill),
            (long)cacheReads.GetValueOrDefault(skill),
            (long)cacheCreations.GetValueOrDefault(skill),
            costs.GetValueOrDefault(skill));

        return new SpendTally(
            models.Keys
                .Concat(new[] { costs, inputs, outputs, cacheReads, cacheCreations }.SelectMany(sums => sums.Keys))
                .Where(skill => skill != Unnamed)
                .Distinct()
                .ToDictionary(skill => skill, SpendOf),
            models,
            Names(effort, EffortAttribute),
            SpendOf(Unnamed),
            period with
            {
                Unreachable = period.Unreachable ?? cost.Unreachable ?? input.Unreachable ?? output.Unreachable ??
                    cacheRead.Unreachable ?? cacheCreation.Unreachable ?? model.Unreachable ?? effort.Unreachable,
            });
    }

    private static EventQuery Turns(DaySpan span) => new(EventName, span.FromUtc, span.UntilUtc);

    private static Dictionary<string, decimal> PerSkill(EventTotals totals) =>
        totals.BySkill().ToDictionary(group => group.Key, group => group.Sum(total => total.Total));

    private static Dictionary<string, IReadOnlyList<string>> Names(EventTotals totals, string attribute) =>
        totals.BySkill()
            .Where(group => group.Key != Unnamed)
            .ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(total => total.Attribute(attribute)).OfType<string>().Distinct().Order()]);
}
