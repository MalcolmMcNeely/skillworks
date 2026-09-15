using Skillworks.Core.Provenance;

namespace Skillworks.Core.Skills;

public sealed record SkillSummary(
    string Name,
    int Activations,
    IReadOnlyList<string> Repositories,
    IReadOnlyList<string> Models,
    IReadOnlyList<string> Efforts,
    SkillSpend Spend,
    IReadOnlyList<SkillOrigin> Origins)
{
    public decimal AverageCost => Activations == 0 ? 0m : Spend.Cost / Activations;
}
