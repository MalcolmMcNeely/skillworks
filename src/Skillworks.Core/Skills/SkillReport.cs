using Skillworks.Core.Activations.Queries;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Filters;
using Skillworks.Core.Provenance;
using Skillworks.Core.Spend;
using Skillworks.Core.Spend.Queries;

namespace Skillworks.Core.Skills;

// Lists catalogue skills that never fired, so a broken description shows up as a zero rather than a gap.
public sealed class SkillReport(
    ActivationQueries activations,
    SpendQueries spend,
    CatalogueSkills catalogue,
    ProvenanceReport provenance,
    Lookback lookback)
{
    public async Task<SkillTable> SkillsAsync(
        Filter filter,
        CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);

        var tallying = activations.TallyBySkillAsync(span, filter, cancellationToken);
        var spending = spend.TallyBySkillAsync(span, filter, cancellationToken);

        var (tally, spent) = (await tallying, await spending);

        var counts = new Dictionary<string, int>(tally.Counts);

        // A never-fired skill's zero belongs to the unfiltered answer; a filter asks what happened, and it did not.
        if (!filter.AsksWhatHappened)
        {
            foreach (var name in catalogue.Names().Where(filter.Covers))
            {
                counts.TryAdd(name, 0);
            }
        }

        // A skill that fired just before the span can still spend inside it, and that spend is real.
        foreach (var name in spent.Spend.Keys)
        {
            counts.TryAdd(name, 0);
        }

        return new SkillTable(
            [
                .. counts
                    .Select(skill => new SkillSummary(
                        skill.Key,
                        skill.Value,
                        tally.Repositories.GetValueOrDefault(skill.Key, []),
                        spent.Models.GetValueOrDefault(skill.Key, []),
                        spent.Efforts.GetValueOrDefault(skill.Key, []),
                        spent.Spend.GetValueOrDefault(skill.Key, SkillSpend.Nothing),
                        tally.Origins.GetValueOrDefault(skill.Key, [])))
                    .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
            ],
            // Turns count beside firings, so a period that only spent is not called quiet.
            provenance.NoteOn(tally.Period.Plus(spent.Period), span),
            span);
    }

    // Offers what fired in the lookback, as the unnarrowed table does, so every choice has something behind it.
    public async Task<FilterChoices> ChoicesAsync(CancellationToken cancellationToken)
    {
        var (repositories, fired) = await activations.ChoicesAsync(lookback.SpanOf(new Filter()), cancellationToken);

        return new FilterChoices(
            repositories,
            [
                // Spellings are told apart exactly, as the filter matches them, or one choice would match half of what it names.
                .. fired
                    .Concat(catalogue.Names())
                    .Distinct()
                    .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
            ]);
    }
}
