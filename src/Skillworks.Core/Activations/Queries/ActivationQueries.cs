using System.Linq.Expressions;
using Microsoft.EntityFrameworkCore;
using Skillworks.Core.EventsStore;
using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;
using Skillworks.Core.TranscriptStore;

namespace Skillworks.Core.Activations.Queries;

public sealed class ActivationQueries(IDbContextFactory<TranscriptStoreDbContext> contexts, EventsStoreReader events)
{
    private const string EventName = "skill_activated";

    private static readonly string[] ByRepository = [EventAttributes.Skill, EventAttributes.Owner, EventAttributes.RepositoryName];

    private readonly record struct SkillValue(string Skill, string? Value);

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
            BySkill(counts).ToDictionary(group => group.Key, group => (int)group.Sum(count => count.Count)),
            BySkill(repositories).ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(count => count.Repository).OfType<string>().Distinct().Order()]),
            BySkill(origins).ToDictionary(
                group => group.Key,
                group => SkillOrigin.Ordered(group.Select(count => SkillOrigin.Of(count.Attribute)))),
            period with { Unreachable = period.Unreachable ?? counts.Unreachable ?? repositories.Unreachable ?? origins.Unreachable });
    }

    public async Task<(IReadOnlyDictionary<string, IReadOnlyList<string>> Models, IReadOnlyDictionary<string, IReadOnlyList<string>> Efforts)> ModelsBySkillAsync(
        Filter filter,
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var activations = Narrowed(store.Activations, filter);

        return (
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Model), cancellationToken),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Effort), cancellationToken));
    }

    // Raw events, as a list shows each firing, so this is the one answer the read cap can cut.
    public async Task<(IReadOnlyList<ActivationSummary> Activations, EventReading Read, EventCounts Period)> ListAsync(
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
    public async Task<(ActivationSummary? Activation, EventReading Read)> OpenAsync(
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

    private static IEnumerable<ActivationSummary> Activations(IEnumerable<TelemetryEvent> recorded) =>
        recorded.Select(ActivationSummary.From).OfType<ActivationSummary>();

    // A count with no skill name is a firing Claude Code did not name, and it belongs to no skill.
    private static IEnumerable<IGrouping<string, EventCount>> BySkill(EventCounts counts) =>
        from count in counts.Groups
        let skill = count.Attribute(EventAttributes.Skill)
        where skill is not null
        group count by skill;

    // Repeated in SpendQueries: sharing it means an interface EF cannot translate or hand-grafted expressions.
    private static IQueryable<Activation> Narrowed(IQueryable<Activation> activations, Filter filter)
    {
        if (filter.FromUtc is { } from)
        {
            activations = activations.Where(a => a.TimestampUtc >= from);
        }

        if (filter.UntilUtc is { } until)
        {
            activations = activations.Where(a => a.TimestampUtc < until);
        }

        if (filter.Repository is { } repository)
        {
            activations = activations.Where(a => a.Repository == repository);
        }

        if (filter.Skill is { } skill)
        {
            activations = activations.Where(a => a.SkillName == skill);
        }

        return activations;
    }

    private static IReadOnlyList<string> Sorted(IEnumerable<string> names) =>
        [.. names.Distinct().OrderBy(name => name, StringComparer.OrdinalIgnoreCase)];

    // Nulls are dropped in memory because SQLite will not take a predicate over the pair.
    private static async Task<IReadOnlyDictionary<string, IReadOnlyList<string>>> BySkillAsync(
        IQueryable<Activation> activations,
        Expression<Func<Activation, SkillValue>> pair,
        CancellationToken cancellationToken)
    {
        var pairs = await activations
            .Select(pair)
            .Distinct()
            .ToListAsync(cancellationToken);

        return pairs
            .Where(pair => pair.Value != null)
            .GroupBy(pair => pair.Skill)
            .ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(pair => pair.Value!).Order()]);
    }
}
