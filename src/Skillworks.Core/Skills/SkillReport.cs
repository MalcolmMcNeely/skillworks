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
    PriceTable prices,
    CatalogueSkills catalogue,
    ProvenanceReport provenance,
    Lookback lookback)
{
    public async Task<SkillTable> SkillsAsync(
        Filter filter,
        CancellationToken cancellationToken)
    {
        var span = lookback.SpanOf(filter);

        // The transcript store is narrowed to the same days, or a week's count would sit beside an all-time cost.
        var spanned = filter with { From = span.From, To = span.To };

        var tally = await activations.TallyBySkillAsync(span, filter, cancellationToken);
        var firedOn = await activations.ModelsBySkillAsync(spanned, cancellationToken);
        var tokens = await spend.TokensBySkillAsync(spanned, cancellationToken);

        // Read now, not stored with the turns, so correcting a rate never means reading a transcript again.
        var rates = await prices.ByModelAsync(cancellationToken);

        var counts = new Dictionary<string, int>(tally.Counts);

        // A never-fired skill's zero belongs to the unfiltered answer; a filter asks what happened, and it did not.
        if (!filter.AsksWhatHappened)
        {
            foreach (var name in catalogue.Names().Where(filter.Covers))
            {
                counts.TryAdd(name, 0);
            }
        }

        // Spend still comes from the transcript store, so a skill can have spend and no firing in the events store.
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
                            Together(firedOn.Models.GetValueOrDefault(skill.Key, []), runs.Select(run => run.Model)),
                            Together(firedOn.Efforts.GetValueOrDefault(skill.Key, []), runs.Select(run => run.Effort)),
                            SkillSpend.Of(runs, rates),
                            tally.Origins.GetValueOrDefault(skill.Key, []));
                    })
                    .OrderBy(summary => summary.Name, StringComparer.OrdinalIgnoreCase)
            ],
            provenance.NoteOn(tally.Period, span),
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

    // The cost covers every request, so a skill billed at two rates must list both models.
    private static IReadOnlyList<string> Together(IReadOnlyList<string> chosen, IEnumerable<string?> ran) =>
        [.. chosen.Concat(ran.OfType<string>()).Distinct().Order()];
}
