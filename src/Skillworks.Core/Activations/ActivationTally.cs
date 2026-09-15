using Skillworks.Core.EventsStore;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

// Period counts every firing in the span, narrowed or not, so a filter that matches nothing is not read as a quiet week.
public sealed record ActivationTally(
    IReadOnlyDictionary<string, int> Counts,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Repositories,
    IReadOnlyDictionary<string, IReadOnlyList<SkillOrigin>> Origins,
    EventTotals Period);
