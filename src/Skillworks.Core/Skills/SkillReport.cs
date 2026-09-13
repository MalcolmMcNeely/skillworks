using Skillworks.Core.Catalogue;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

/// <summary>
/// Answers "which skills fired, how often, and where", and names the catalogue skills that never
/// fired so a broken description shows up as a zero rather than a gap.
/// </summary>
public sealed class SkillReport(ActivationStore activations, CatalogueSkills catalogue)
{
    public async Task<IReadOnlyList<SkillSummary>> SkillsAsync(CancellationToken cancellationToken)
    {
        var tally = await activations.TallyBySkillAsync(cancellationToken);
        var counts = new Dictionary<string, int>(tally.Counts);

        foreach (var name in catalogue.Names())
        {
            counts.TryAdd(name, 0);
        }

        return
        [
            .. counts
                .Select(skill => new SkillSummary(
                    skill.Key,
                    skill.Value,
                    tally.Repositories.GetValueOrDefault(skill.Key, []),
                    tally.Branches.GetValueOrDefault(skill.Key, [])))
                .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
        ];
    }
}
