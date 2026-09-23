using Skillworks.Core.Dashboard.Activations;
using Skillworks.Core.Dashboard.Activations.Queries;
using Skillworks.Core.Dashboard.Spend;
using Skillworks.Core.Dashboard.Spend.Queries;
using Skillworks.Core.Shared.Arriving;
using Skillworks.Core.Shared.Catalogue;
using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Dashboard.Skills;

// Lists catalogue skills that never fired, so a broken description shows up as a zero rather than a gap.
public sealed class SkillReport(
    ActivationQueries activations,
    SpendQueries spend,
    CatalogueSkills catalogue,
    ArrivingDays arriving,
    Lookback lookback)
{
    public IAsyncEnumerable<ArrivingLine> AnswerAsync(Filter filter, CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);
        var days = span.NewestFirst();

        var head = new SkillsHead(
            span,
            days,
            // A never-fired skill's zero belongs to the unfiltered answer; a filter asks what happened, and it did not.
            filter.AsksWhatHappened
                ? []
                : [.. catalogue.Names().Where(filter.Covers).Order(StringComparer.OrdinalIgnoreCase)]);

        return arriving.AnswerAsync(head, days, (day, token) => DayAsync(day, filter, token), cancellationToken);
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

        // Turns count beside Activations, so a period that only spent is not called quiet.
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
            tally.HoursOf(name),
            tally.Triggers.GetValueOrDefault(name, []),
            tally.Repositories.GetValueOrDefault(name, []),
            spendNamed ? spent.Models.GetValueOrDefault(name, []) : null,
            spendNamed ? spent.Efforts.GetValueOrDefault(name, []) : null,
            spendNamed ? spent.Spend.GetValueOrDefault(name, TurnTotals.Nothing) : null,
            origins);
    }
}
