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

    // Raw events, as a list shows each firing, so this is the one answer the read cap can cut.
    public async Task<(IReadOnlyList<Activation> Activations, EventReading Read, EventTotals Period)> ListAsync(
        DaySpan span,
        Filter filter,
        CancellationToken cancellationToken)
    {
        var reading = events.ReadAsync(Firings(span, filter), cancellationToken);
        var surveying = events.CountAsync(Firings(span), [], cancellationToken);

        var (read, period) = (await reading, await surveying);

        return ([.. Activations(read.Events).OrderByDescending(activation => activation.TimestampUtc)], read, period);
    }

    // Not narrowed by a filter: a reader who has a firing's id is asking about that firing, not a week.
    public async Task<(Activation? Activation, EventReading Read)> OpenAsync(
        ActivationId id,
        CancellationToken cancellationToken)
    {
        var around = new EventQuery(EventName, id.ReadFrom, id.ReadUntil) { Session = id.Session, Sequence = id.Sequence };
        var read = await events.ReadAsync(around, cancellationToken);

        return (Activations(read.Events.Where(recorded => ActivationId.Of(recorded) == id)).FirstOrDefault(), read);
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

    private static IEnumerable<Activation> Activations(IEnumerable<TelemetryEvent> recorded) =>
        recorded.Select(Activation.From).OfType<Activation>();

    private static IReadOnlyList<string> Sorted(IEnumerable<string> names) =>
        [.. names.Distinct().OrderBy(name => name, StringComparer.OrdinalIgnoreCase)];
}
