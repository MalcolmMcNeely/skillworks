using Skillworks.Core.Catalogue;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

/// <summary>
/// Answers "which skills fired, how often, where, and what did they cost", and names the catalogue
/// skills that never fired so a broken description shows up as a zero rather than a gap.
/// </summary>
public sealed class SkillReport(ActivationStore activations, SpendStore spend, PriceTable prices, CatalogueSkills catalogue)
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
                .Select(skill =>
                {
                    var runs = tokens.GetValueOrDefault(skill.Key, []);

                    return new SkillSummary(
                        skill.Key,
                        skill.Value,
                        tally.Repositories.GetValueOrDefault(skill.Key, []),
                        tally.Branches.GetValueOrDefault(skill.Key, []),
                        Together(tally.Models.GetValueOrDefault(skill.Key, []), runs.Select(run => run.Model)),
                        Together(tally.Efforts.GetValueOrDefault(skill.Key, []), runs.Select(run => run.Effort)),
                        SkillSpend.Of(runs, rates));
                })
                .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
        ];
    }

    /// <summary>
    /// What the skill was chosen at, and what its own requests ran at, in one list. The cost beside
    /// it covers the requests, so a skill charged at two rates must not read as if it were charged
    /// at one.
    /// </summary>
    private static IReadOnlyList<string> Together(IReadOnlyList<string> chosen, IEnumerable<string?> ran) =>
        [.. chosen.Concat(ran.OfType<string>()).Distinct().Order()];
}
