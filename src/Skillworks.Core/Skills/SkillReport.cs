using Skillworks.Core.Catalogue;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

/// <summary>
/// Answers "which skills fired, how often, where, and what did they cost", and names the catalogue
/// skills that never fired so a broken description shows up as a zero rather than a gap.
/// </summary>
public sealed class SkillReport(ActivationStore activations, SpendStore spend, PriceBook prices, CatalogueSkills catalogue)
{
    public async Task<IReadOnlyList<SkillSummary>> SkillsAsync(CancellationToken cancellationToken)
    {
        var tally = await activations.TallyBySkillAsync(cancellationToken);
        var tokens = await spend.TokensBySkillAsync(cancellationToken);

        // Read now rather than stored with the turns, so yesterday's spend is costed at today's
        // prices and correcting a rate never means reading a transcript again.
        var rates = await prices.ByModelAsync(cancellationToken);

        var counts = new Dictionary<string, int>(tally.Counts);

        foreach (var name in catalogue.Names())
        {
            counts.TryAdd(name, 0);
        }

        // A skill can own tokens without a firing of its own in the store: the transcript that held
        // the firing may not have been read yet, or may have been trimmed away.
        foreach (var name in tokens.Keys)
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
                    tally.Branches.GetValueOrDefault(skill.Key, []),
                    tally.Models.GetValueOrDefault(skill.Key, []),
                    tally.Efforts.GetValueOrDefault(skill.Key, []),
                    SkillSpend.Of(tokens.GetValueOrDefault(skill.Key, []), rates)))
                .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
        ];
    }
}
