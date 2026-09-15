using System.Runtime.CompilerServices;
using Skillworks.Core.Activations;
using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Arriving;
using Skillworks.Core.Catalogue;
using Skillworks.Core.EventsStore;
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
    public async IAsyncEnumerable<ArrivingLine> AnswerAsync(
        Filter filter,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var days = span.NewestFirst();

        yield return new SkillsHead(
            span,
            days,
            // A never-fired skill's zero belongs to the unfiltered answer; a filter asks what happened, and it did not.
            filter.AsksWhatHappened
                ? []
                : [.. catalogue.Names().Where(filter.Covers).Order(StringComparer.OrdinalIgnoreCase)]);

        var read = EventTotals.Of([]);

        foreach (var day in days)
        {
            var (line, period) = await DayAsync(day, filter, cancellationToken);

            read = read.Plus(period);

            if (period.Unreachable is not null)
            {
                break;
            }

            yield return line;
        }

        yield return new AnswerEnd(gaps.InTotals(read));
    }

    // Every query for the day runs before the next day starts, so a day is whole when it lands.
    private async Task<(SkillsDay Line, EventTotals Period)> DayAsync(
        DateOnly day,
        Filter filter,
        CancellationToken cancellationToken)
    {
        var tallying = activations.TallyBySkillAsync(DaySpan.Of(day), filter, cancellationToken);
        var spending = spend.TallyBySkillAsync(DaySpan.Of(day), filter, cancellationToken);

        var (tally, spent) = (await tallying, await spending);

        // Turns count beside firings, so a period that only spent is not called quiet.
        var period = tally.Period.Plus(spent.Period);

        return (
            new SkillsDay(
                day,
                [
                    // A skill that fired on an earlier day can still spend on this one, and that spend is real.
                    .. tally.Counts.Keys
                        .Union(spent.Spend.Keys)
                        .Select(name => Summary(name, tally, spent))
                        .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
                ],
                // Some of it may be another skill's, and beside one skill all of it would read as that skill's.
                filter.Skill is null ? spent.Unnamed : null,
                (long)period.Total),
            period);
    }

    private static SkillSummary Summary(string name, ActivationTally tally, SpendTally spent)
    {
        var origins = tally.Origins.GetValueOrDefault(name, []);

        // A plugin outside Anthropic's marketplaces has its Turns sent as "third-party", so none under its name is not a zero.
        var spendNamed = spent.Spend.ContainsKey(name) || !origins.Any(origin => origin.DeliveredByPlugin);

        return new SkillSummary(
            name,
            tally.Counts.GetValueOrDefault(name),
            tally.Repositories.GetValueOrDefault(name, []),
            spendNamed ? spent.Models.GetValueOrDefault(name, []) : null,
            spendNamed ? spent.Efforts.GetValueOrDefault(name, []) : null,
            spendNamed ? spent.Spend.GetValueOrDefault(name, TurnTotals.Nothing) : null,
            origins);
    }

    // Offers what fired in the lookback, the span of the unnarrowed answer, so every choice has something behind it.
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
