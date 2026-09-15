using Skillworks.Core.Provenance;
using Skillworks.Core.Spend;

namespace Skillworks.Core.Skills;

// Null where the skill's Turns went unnamed, as an empty list or a zero would say it spent nothing.
public sealed record SkillSummary(
    string Name,
    int Activations,
    IReadOnlyList<string> Repositories,
    IReadOnlyList<string>? Models,
    IReadOnlyList<string>? Efforts,
    SkillSpend? Spend,
    IReadOnlyList<SkillOrigin> Origins)
{
    public decimal? AverageCost => Spend switch
    {
        null => null,
        _ when Activations == 0 => 0m,
        _ => Spend.Cost / Activations,
    };
}
