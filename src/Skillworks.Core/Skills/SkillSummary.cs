using Skillworks.Core.Shared.Provenance;
using Skillworks.Core.Spend;

namespace Skillworks.Core.Skills;

// Null where the skill's Turns went unnamed, as an empty list or a zero would say it spent nothing.
public sealed record SkillSummary(
    string Name,
    int Activations,
    // By UTC hour, as the Filter counts whole UTC days.
    IReadOnlyList<int> Hours,
    IReadOnlyList<TriggerCount> Triggers,
    IReadOnlyList<string> Repositories,
    IReadOnlyList<string>? Models,
    IReadOnlyList<string>? Efforts,
    TurnTotals? Spend,
    IReadOnlyList<SkillOrigin> Origins);
