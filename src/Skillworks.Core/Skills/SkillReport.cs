using Skillworks.Core.Catalogue;
using Skillworks.Core.Provenance;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Skills;

/// <summary>
/// Answers "which skills fired, how often, where, from where, and what did they cost", and names
/// the catalogue skills that never fired so a broken description shows up as a zero rather than a
/// gap. The two stores meet here, on skill name and period.
/// </summary>
public sealed class SkillReport(
    ActivationStore activations,
    SpendStore spend,
    PriceTable prices,
    CatalogueSkills catalogue,
    ProvenanceReport provenance)
{
    public async Task<SkillTable> SkillsAsync(
        TelemetryFilter filter,
        CancellationToken cancellationToken)
    {
        var tally = await activations.TallyBySkillAsync(filter, cancellationToken);
        var tokens = await spend.TokensBySkillAsync(filter, cancellationToken);
        var origins = await provenance.ForAsync(filter, cancellationToken);

        // Read now rather than stored with the turns, so yesterday's spend is costed at today's
        // prices and correcting a rate never means reading a transcript again.
        var rates = await prices.ByModelAsync(cancellationToken);

        var counts = new Dictionary<string, int>(tally.Counts);

        // A skill that never fired belongs to the all-time, everywhere answer, where its zero is the
        // point. A filter that asks what happened in one week or one project is asking about events,
        // and a skill with no events there is not a zero in that answer: it is not in it.
        if (!filter.AsksWhatHappened)
        {
            foreach (var name in catalogue.Names().Where(filter.Covers))
            {
                counts.TryAdd(name, 0);
            }
        }

        // A skill can own tokens without a firing of its own in the store: the transcript that held
        // the firing may not have been read yet, or may have been trimmed away.
        foreach (var name in tokens.Keys)
        {
            counts.TryAdd(name, 0);
        }

        return new SkillTable(
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
                            SkillSpend.Of(runs, rates),
                            origins.Of(skill.Key));
                    })
                    .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
            ],
            origins.Note);
    }

    /// <summary>
    /// What the three filters can be set to. The catalogue is in the skill names as well as the
    /// history, so a skill can be followed from the day it is written rather than the day it first
    /// fires.
    /// </summary>
    public async Task<FilterChoices> ChoicesAsync(CancellationToken cancellationToken)
    {
        var (repositories, fired) = await activations.ChoicesAsync(cancellationToken);

        return new FilterChoices(
            repositories,
            [
                // Told apart exactly, because that is how the filter matches them. Folding two
                // spellings into one choice would offer a name that then matches only half of what
                // it appears to name.
                .. fired
                    .Concat(catalogue.Names())
                    .Distinct()
                    .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
            ]);
    }

    /// <summary>
    /// What the skill was chosen at, and what its own requests ran at, in one list. The cost beside
    /// it covers the requests, so a skill charged at two rates must not read as if it were charged
    /// at one.
    /// </summary>
    private static IReadOnlyList<string> Together(IReadOnlyList<string> chosen, IEnumerable<string?> ran) =>
        [.. chosen.Concat(ran.OfType<string>()).Distinct().Order()];
}
