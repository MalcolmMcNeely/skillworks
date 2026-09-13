using Microsoft.EntityFrameworkCore;

namespace Skillworks.Core.Telemetry;

/// <summary>Everything the store knows about the skills that fired, gathered in one read.</summary>
/// <param name="Counts">Activations per skill. A skill absent here never fired.</param>
/// <param name="Repositories">Distinct repositories per skill, sorted.</param>
/// <param name="Branches">Distinct git branches per skill, sorted.</param>
public sealed record ActivationTally(
    IReadOnlyDictionary<string, int> Counts,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Repositories,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Branches);

/// <summary>
/// Reads the activations back out. It sits beside the ingest that writes them, so the store's shape
/// is known in one place and callers see tallies rather than tables.
/// </summary>
public sealed class ActivationStore(IDbContextFactory<TelemetryDbContext> contexts)
{
    private readonly record struct SkillValue(string Skill, string Value);

    private readonly record struct SkillCount(string Skill, int Activations);

    public async Task<ActivationTally> TallyBySkillAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        // Three narrow reads beat one wide one. SQLite has no distinct-within-group, and pulling
        // every activation back to fold it in memory would not survive a full transcript folder.
        var counts = await store.Activations
            .GroupBy(a => a.SkillName)
            .Select(group => new SkillCount(group.Key, group.Count()))
            .ToListAsync(cancellationToken);

        var repositories = await store.Activations
            .Where(a => a.Repository != null)
            .Select(a => new SkillValue(a.SkillName, a.Repository!))
            .Distinct()
            .ToListAsync(cancellationToken);

        var branches = await store.Activations
            .Where(a => a.GitBranch != null)
            .Select(a => new SkillValue(a.SkillName, a.GitBranch!))
            .Distinct()
            .ToListAsync(cancellationToken);

        return new ActivationTally(
            counts.ToDictionary(count => count.Skill, count => count.Activations),
            BySkill(repositories),
            BySkill(branches));
    }

    private static Dictionary<string, IReadOnlyList<string>> BySkill(List<SkillValue> pairs) =>
        pairs
            .GroupBy(pair => pair.Skill)
            .ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(pair => pair.Value).Order()]);
}
