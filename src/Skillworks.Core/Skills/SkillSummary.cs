namespace Skillworks.Core.Skills;

/// <summary>One row of the skill table, shaped so the front end can render it without arithmetic.</summary>
/// <param name="Name">As invoked: <c>&lt;plugin&gt;:&lt;skill&gt;</c> for a skill delivered by a plugin.</param>
/// <param name="Activations">How many times it fired. Zero means it exists and never has.</param>
/// <param name="Repositories">Distinct repositories it fired in, sorted.</param>
/// <param name="Branches">Distinct git branches it fired on, sorted.</param>
/// <param name="Models">Distinct models that fired it, sorted, so like is compared with like.</param>
/// <param name="Efforts">Distinct effort levels it fired at, sorted.</param>
/// <param name="Spend">What the requests made under it cost.</param>
public sealed record SkillSummary(
    string Name,
    int Activations,
    IReadOnlyList<string> Repositories,
    IReadOnlyList<string> Branches,
    IReadOnlyList<string> Models,
    IReadOnlyList<string> Efforts,
    SkillSpend Spend)
{
    /// <summary>
    /// What one firing costs on average, so a skill used twice a year at a pound a time is not
    /// hidden behind a cheap one used daily. Zero when it has never fired and there is no average.
    /// </summary>
    public decimal AverageCost => Activations == 0 ? 0m : Spend.Cost / Activations;
}
