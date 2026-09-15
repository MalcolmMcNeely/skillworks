using System.Linq.Expressions;
using Microsoft.EntityFrameworkCore;
using Skillworks.Core.Filters;
using Skillworks.Core.TranscriptStore;

namespace Skillworks.Core.Activations.Stores;

public sealed class ActivationStore(IDbContextFactory<TranscriptStoreDbContext> contexts)
{
    private readonly record struct SkillValue(string Skill, string? Value);

    private readonly record struct SkillCount(string Skill, int Activations);

    public async Task<ActivationTally> TallyBySkillAsync(TelemetryFilter filter, CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var activations = Narrowed(store.Activations, filter);

        // Narrow reads beat one wide one. SQLite has no distinct-within-group, and pulling every
        // activation back to fold it in memory would not survive a full transcript folder.
        var counts = await activations
            .GroupBy(a => a.SkillName)
            .Select(group => new SkillCount(group.Key, group.Count()))
            .ToListAsync(cancellationToken);

        return new ActivationTally(
            counts.ToDictionary(count => count.Skill, count => count.Activations),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Repository), cancellationToken),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.GitBranch), cancellationToken),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Model), cancellationToken),
            await BySkillAsync(activations, a => new SkillValue(a.SkillName, a.Effort), cancellationToken));
    }

    public async Task<IReadOnlyList<ActivationSummary>> ListAsync(
        TelemetryFilter filter,
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        return await Narrowed(store.Activations, filter)
            .OrderByDescending(a => a.TimestampUtc)
            .Select(a => new ActivationSummary(
                a.ToolUseId,
                a.SkillName,
                a.Repository,
                a.GitBranch,
                a.Model,
                a.Effort,
                a.TimestampUtc))
            .ToListAsync(cancellationToken);
    }

    // Not narrowed by a filter: a reader who has a firing's id is asking about that firing, not a week.
    public async Task<ActivationDetail?> OpenAsync(string id, CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var activation = await store.Activations
            .AsNoTracking()
            .FirstOrDefaultAsync(a => a.ToolUseId == id, cancellationToken);

        return activation is null
            ? null
            : new ActivationDetail(
                activation.ToolUseId,
                activation.SkillName,
                activation.SessionId,
                activation.Repository,
                activation.GitBranch,
                activation.Model,
                activation.Effort,
                activation.TimestampUtc,
                RecordedArguments.Read(activation.Arguments));
    }

    // Not narrowed: a filter that has cut the answer to nothing must still offer the way back out.
    public async Task<(IReadOnlyList<string> Repositories, IReadOnlyList<string> Skills)> ChoicesAsync(
        CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        var repositories = await store.Activations
            .Select(a => a.Repository)
            .Distinct()
            .ToListAsync(cancellationToken);

        var skills = await store.Activations
            .Select(a => a.SkillName)
            .Distinct()
            .ToListAsync(cancellationToken);

        return (Sorted(repositories.OfType<string>()), Sorted(skills));
    }

    // Repeated in SpendStore: sharing it means an interface EF cannot translate or hand-grafted expressions.
    private static IQueryable<Activation> Narrowed(IQueryable<Activation> activations, TelemetryFilter filter)
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
        [.. names.OrderBy(name => name, StringComparer.OrdinalIgnoreCase)];

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
