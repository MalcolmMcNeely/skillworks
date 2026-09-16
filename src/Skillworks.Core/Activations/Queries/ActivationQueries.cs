using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations.Queries;

public sealed partial class ActivationQueries(EventsStoreReader events)
{
    private const string EventName = "skill_activated";

    private static readonly string[] ByRepository = [EventAttributes.Skill, EventAttributes.Owner, EventAttributes.RepositoryName];

    // Narrow counts, not one wide one: every pairing multiplies the series a store returns, and a store caps them.
    public async Task<ActivationTally> TallyBySkillAsync(DaySpan span, Filter filter, CancellationToken cancellationToken)
    {
        var narrowed = Firings(span, filter);

        var timing = events.CountByHourAsync(narrowed, [EventAttributes.Skill], cancellationToken);
        var placing = events.CountAsync(narrowed, ByRepository, cancellationToken);
        var tracing = events.CountAsync(narrowed, [EventAttributes.Skill, .. SkillOrigin.Attributes], cancellationToken);
        var surveying = events.CountAsync(Firings(span), [], cancellationToken);

        var (timed, repositories, origins, period) = (await timing, await placing, await tracing, await surveying);

        var hours = timed.BySkill().ToDictionary(group => group.Key, IReadOnlyList<int> (group) => ByHour(group));

        // One query answers both the Origins and the Activations by trigger, so each firing is read once.
        var traced = origins.BySkill().ToDictionary(
            group => group.Key,
            group => group.Select(count => (Origin: SkillOrigin.Of(count.Attribute), count.Total)).ToArray());

        return new ActivationTally(
            // From the hours, so a day's Activations and its hours never disagree.
            hours.ToDictionary(skill => skill.Key, skill => skill.Value.Sum()),
            hours,
            traced.ToDictionary(
                skill => skill.Key,
                skill => TriggerCount.Ordered(skill.Value.Select(traced => (traced.Origin.Trigger, traced.Total)))),
            repositories.BySkill().ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(count => count.Repository).OfType<string>().Distinct().Order()]),
            traced.ToDictionary(skill => skill.Key, skill => SkillOrigin.Ordered(skill.Value.Select(traced => traced.Origin))),
            period with { Unreachable = period.Unreachable ?? timed.Unreachable ?? repositories.Unreachable ?? origins.Unreachable });
    }

    private static int[] ByHour(IEnumerable<EventTotal> counts)
    {
        var hours = new int[ActivationTally.HoursInDay];

        foreach (var count in counts)
        {
            if (count.StartOfHour is { } startOfHour)
            {
                hours[startOfHour.Hour] += (int)count.Total;
            }
        }

        return hours;
    }

    public async Task<(IReadOnlyList<string> Repositories, EventTotals Period)> RepositoriesAsync(
        DaySpan span,
        CancellationToken cancellationToken)
    {
        var fired = await events.CountAsync(Firings(span), [EventAttributes.Owner, EventAttributes.RepositoryName], cancellationToken);

        return (
            [
                .. fired.Groups
                    .Select(count => count.Repository)
                    .OfType<string>()
                    .Distinct()
                    .OrderBy(repository => repository, StringComparer.OrdinalIgnoreCase)
            ],
            fired);
    }

    private static EventQuery Firings(DaySpan span) => new(EventName, span.FromUtc, span.UntilUtc);

    private static EventQuery Firings(DaySpan span, Filter filter) =>
        Firings(span) with { Repository = filter.Repository, Skill = filter.Skill };
}
