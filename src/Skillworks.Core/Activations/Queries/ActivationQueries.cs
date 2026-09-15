using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations.Queries;

public sealed class ActivationQueries(EventsStoreReader events)
{
    private const string EventName = "skill_activated";

    private static readonly string[] ByRepository = [EventAttributes.Skill, EventAttributes.Owner, EventAttributes.RepositoryName];

    // Narrow counts, not one wide one: every pairing multiplies the series a store returns, and a store caps them.
    public async Task<ActivationTally> TallyBySkillAsync(DaySpan span, Filter filter, CancellationToken cancellationToken)
    {
        var narrowed = Firings(span, filter);

        var counting = events.CountAsync(narrowed, [EventAttributes.Skill], cancellationToken);
        var placing = events.CountAsync(narrowed, ByRepository, cancellationToken);
        var tracing = events.CountAsync(narrowed, [EventAttributes.Skill, .. SkillOrigin.Attributes], cancellationToken);
        var surveying = events.CountAsync(Firings(span), [], cancellationToken);

        var (counts, repositories, origins, period) = (await counting, await placing, await tracing, await surveying);

        return new ActivationTally(
            counts.BySkill().ToDictionary(group => group.Key, group => (int)group.Sum(count => count.Total)),
            repositories.BySkill().ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(count => count.Repository).OfType<string>().Distinct().Order()]),
            origins.BySkill().ToDictionary(
                group => group.Key,
                group => SkillOrigin.Ordered(group.Select(count => SkillOrigin.Of(count.Attribute)))),
            period with { Unreachable = period.Unreachable ?? counts.Unreachable ?? repositories.Unreachable ?? origins.Unreachable });
    }

    // Not narrowed by a filter: a filter that has cut the answer to nothing must still offer the way back out.
    public async Task<(IReadOnlyList<string> Repositories, IReadOnlyList<string> Skills)> ChoicesAsync(
        DaySpan span,
        CancellationToken cancellationToken)
    {
        var fired = await events.CountAsync(Firings(span), ByRepository, cancellationToken);

        return (
            Sorted(fired.Groups.Select(count => count.Repository).OfType<string>()),
            Sorted(fired.Groups.Select(count => count.Attribute(EventAttributes.Skill)).OfType<string>()));
    }

    private static EventQuery Firings(DaySpan span) => new(EventName, span.FromUtc, span.UntilUtc);

    private static EventQuery Firings(DaySpan span, Filter filter) =>
        Firings(span) with { Repository = filter.Repository, Skill = filter.Skill };

    private static IReadOnlyList<string> Sorted(IEnumerable<string> names) =>
        [.. names.Distinct().OrderBy(name => name, StringComparer.OrdinalIgnoreCase)];
}
