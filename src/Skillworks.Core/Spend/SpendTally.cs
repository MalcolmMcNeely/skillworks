using Skillworks.Core.EventsStore;

namespace Skillworks.Core.Spend;

// Period counts every Turn in the span, narrowed or not, as ActivationTally counts every firing.
public sealed record SpendTally(
    IReadOnlyDictionary<string, SkillSpend> Spend,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Models,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Efforts,
    EventTotals Period);
