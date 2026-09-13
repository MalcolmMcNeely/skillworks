using Microsoft.EntityFrameworkCore;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

/// <summary>
/// Answers "which skills fired, how often, and where" from the parsed transcripts, and names the
/// catalogue skills that never fired so a broken description shows up as a zero rather than a gap.
/// </summary>
public sealed class SkillReport(IDbContextFactory<TelemetryDbContext> contexts, CatalogueSkills catalogue)
{
    private readonly record struct SkillValue(string Skill, string Value);

    private readonly record struct SkillCount(string Skill, int Activations);

    public async Task<IReadOnlyList<SkillSummary>> SkillsAsync(CancellationToken cancellationToken)
    {
        await using var store = await contexts.CreateDbContextAsync(cancellationToken);

        // Three narrow reads beat one wide one. SQLite has no distinct-within-group, and pulling
        // every activation back to fold it in memory would not survive a real history.
        var counts = await store.Activations
            .GroupBy(a => a.SkillName)
            .Select(group => new SkillCount(group.Key, group.Count()))
            .ToListAsync(cancellationToken);

        var repositories = Fold(await store.Activations
            .Where(a => a.Repository != null)
            .Select(a => new SkillValue(a.SkillName, a.Repository!))
            .Distinct()
            .ToListAsync(cancellationToken));

        var branches = Fold(await store.Activations
            .Where(a => a.GitBranch != null)
            .Select(a => new SkillValue(a.SkillName, a.GitBranch!))
            .Distinct()
            .ToListAsync(cancellationToken));

        var fired = counts.ToDictionary(count => count.Skill, count => count.Activations);

        foreach (var name in catalogue.Names())
        {
            fired.TryAdd(name, 0);
        }

        return
        [
            .. fired
                .Select(skill => new SkillSummary(
                    skill.Key,
                    skill.Value,
                    repositories.GetValueOrDefault(skill.Key, []),
                    branches.GetValueOrDefault(skill.Key, [])))
                .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
        ];
    }

    private static Dictionary<string, IReadOnlyList<string>> Fold(List<SkillValue> pairs) =>
        pairs
            .GroupBy(pair => pair.Skill)
            .ToDictionary(
                group => group.Key,
                IReadOnlyList<string> (group) => [.. group.Select(pair => pair.Value).Order()]);
}
