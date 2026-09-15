using Skillworks.Core.Activations;
using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;
using Skillworks.Core.Spend;
using Skillworks.Core.Spend.Queries;

namespace Skillworks.Core.Skills;

// Lists catalogue skills that never fired, so a broken description shows up as a zero rather than a gap.
public sealed class SkillReport(
    ActivationQueries activations,
    SpendQueries spend,
    CatalogueSkills catalogue,
    GapReport gaps,
    Lookback lookback)
{
    public async Task<SkillTable> SkillsAsync(
        Filter filter,
        CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);

        var tallying = activations.TallyBySkillAsync(span, filter, cancellationToken);
        var spending = spend.TallyBySkillAsync(span, filter, cancellationToken);

        var (tally, spent) = (await tallying, await spending);

        var counts = new Dictionary<string, int>(tally.Counts);

        // A never-fired skill's zero belongs to the unfiltered answer; a filter asks what happened, and it did not.
        if (!filter.AsksWhatHappened)
        {
            foreach (var name in catalogue.Names().Where(filter.Covers))
            {
                counts.TryAdd(name, 0);
            }
        }

        // A skill that fired just before the span can still spend inside it, and that spend is real.
        foreach (var name in spent.Spend.Keys)
        {
            counts.TryAdd(name, 0);
        }

        return new SkillTable(
            [
                .. counts
                    .Select(skill => Summary(skill.Key, skill.Value, tally, spent))
                    .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
            ],
            // Some of it may be another skill's, and on this skill's page all of it would read as its own.
            filter.Skill is null ? spent.Unnamed : null,
            // Turns count beside firings, so a period that only spent is not called quiet.
            gaps.InTotals(tally.Period.Plus(spent.Period)),
            span);
    }

    private static SkillSummary Summary(string name, int activations, ActivationTally tally, SpendTally spent)
    {
        var origins = tally.Origins.GetValueOrDefault(name, []);

        // A plugin outside Anthropic's marketplaces has its Turns sent as "third-party", so none under its name is not a zero.
        var spendNamed = spent.Spend.ContainsKey(name) || !origins.Any(origin => origin.DeliveredByPlugin);

        return new SkillSummary(
            name,
            activations,
            tally.Repositories.GetValueOrDefault(name, []),
            spendNamed ? spent.Models.GetValueOrDefault(name, []) : null,
            spendNamed ? spent.Efforts.GetValueOrDefault(name, []) : null,
            spendNamed ? spent.Spend.GetValueOrDefault(name, TurnTotals.Nothing) : null,
            origins);
    }

    // Offers what fired in the lookback, as the unnarrowed table does, so every choice has something behind it.
    public async Task<FilterChoices> ChoicesAsync(CancellationToken cancellationToken)
    {
        var (repositories, fired) = await activations.ChoicesAsync(lookback.SpanOf(new Filter()), cancellationToken);

        return new FilterChoices(
            repositories,
            [
                // Spellings are told apart exactly, as the filter matches them, or one choice would match half of what it names.
                .. fired
                    .Concat(catalogue.Names())
                    .Distinct()
                    .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
            ]);
    }
}
