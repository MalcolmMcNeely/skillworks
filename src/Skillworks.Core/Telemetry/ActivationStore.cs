using System.Linq.Expressions;
using Microsoft.EntityFrameworkCore;

namespace Skillworks.Core.Telemetry;

/// <summary>Everything the store knows about the skills that fired, gathered in one read.</summary>
/// <param name="Counts">Activations per skill. A skill absent here never fired.</param>
/// <param name="Repositories">Distinct repositories per skill, sorted.</param>
/// <param name="Branches">Distinct git branches per skill, sorted.</param>
/// <param name="Models">Distinct models per skill, sorted.</param>
/// <param name="Efforts">Distinct effort levels per skill, sorted.</param>
public sealed record ActivationTally(
    IReadOnlyDictionary<string, int> Counts,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Repositories,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Branches,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Models,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Efforts);

/// <summary>
/// Reads the activations back out. It sits beside the ingest that writes them, so the store's shape
/// is known in one place and callers see tallies rather than tables.
/// </summary>
public sealed class ActivationStore(IDbContextFactory<TelemetryDbContext> contexts)
{
    private readonly record struct SkillValue(string Skill, string? Value);

    private readonly record struct SkillCount(string Skill, int Activations);

    public async Task<ActivationTally> TallyBySkillAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        // Narrow reads beat one wide one. SQLite has no distinct-within-group, and pulling every
        // activation back to fold it in memory would not survive a full transcript folder.
        var counts = await store.Activations
            .GroupBy(a => a.SkillName)
            .Select(group => new SkillCount(group.Key, group.Count()))
            .ToListAsync(cancellationToken);

        return new ActivationTally(
            counts.ToDictionary(count => count.Skill, count => count.Activations),
            await DistinctAsync(store, a => new SkillValue(a.SkillName, a.Repository), cancellationToken),
            await DistinctAsync(store, a => new SkillValue(a.SkillName, a.GitBranch), cancellationToken),
            await DistinctAsync(store, a => new SkillValue(a.SkillName, a.Model), cancellationToken),
            await DistinctAsync(store, a => new SkillValue(a.SkillName, a.Effort), cancellationToken));
    }

    /// <summary>
    /// The distinct values of one column per skill. Taking the whole pair as an expression keeps
    /// the distinct in SQLite, which is the point: only the handful of pairs a skill actually has
    /// comes back, never a row per activation. The rows that recorded nothing are dropped here,
    /// because a predicate over a projected pair is the one thing SQLite will not be told.
    /// </summary>
    private static async Task<IReadOnlyDictionary<string, IReadOnlyList<string>>> DistinctAsync(
        TelemetryDbContext store,
        Expression<Func<Activation, SkillValue>> column,
        CancellationToken cancellationToken)
    {
        var pairs = await store.Activations
            .Select(column)
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
