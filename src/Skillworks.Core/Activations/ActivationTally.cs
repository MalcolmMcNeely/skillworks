using Skillworks.Core.EventsStore;
using Skillworks.Core.Provenance;

namespace Skillworks.Core.Activations;

// Period counts every Activation in the span, narrowed or not, so a filter that matches nothing is not read as a quiet week.
public sealed record ActivationTally(
    IReadOnlyDictionary<string, int> Counts,
    // By UTC hour, as the Filter counts whole UTC days.
    IReadOnlyDictionary<string, IReadOnlyList<int>> Hours,
    IReadOnlyDictionary<string, IReadOnlyList<TriggerCount>> Triggers,
    IReadOnlyDictionary<string, IReadOnlyList<string>> Repositories,
    IReadOnlyDictionary<string, IReadOnlyList<SkillOrigin>> Origins,
    EventTotals Period)
{
    public const int HoursInDay = 24;

    // Every hour even for a skill that only spent, so a quiet hour is a zero, not a slot left out.
    public IReadOnlyList<int> HoursOf(string skill) => Hours.GetValueOrDefault(skill) ?? new int[HoursInDay];
}
