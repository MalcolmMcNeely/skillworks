using Skillworks.Core.Provenance;

namespace Skillworks.Core.Skills;

/// <summary>One row of the skill table, shaped so the front end can render it without arithmetic.</summary>
/// <param name="Name">As invoked: <c>&lt;plugin&gt;:&lt;skill&gt;</c> for a skill delivered by a plugin.</param>
/// <param name="Activations">How many times it fired. Zero means it exists and never has.</param>
/// <param name="Repositories">Distinct repositories it fired in, sorted.</param>
/// <param name="Branches">Distinct git branches it fired on, sorted.</param>
/// <param name="Models">
/// Distinct models it was chosen by and ran on, sorted, so the cost beside them is compared with
/// like: a skill charged at two rates does not read as one charged at a single rate.
/// </param>
/// <param name="Efforts">Distinct effort levels it was chosen at and ran at, sorted.</param>
/// <param name="Spend">What the requests made under it cost.</param>
/// <param name="Origins">
/// Every way the events store saw this name delivered and set off inside the period. Empty means
/// the store said nothing about it, which the note beside the table explains: it is never a count
/// of zero.
/// </param>
public sealed record SkillSummary(
    string Name,
    int Activations,
    IReadOnlyList<string> Repositories,
    IReadOnlyList<string> Branches,
    IReadOnlyList<string> Models,
    IReadOnlyList<string> Efforts,
    SkillSpend Spend,
    IReadOnlyList<SkillOrigin> Origins)
{
    /// <summary>
    /// What one firing costs on average, so a skill used twice a year at a pound a time is not
    /// hidden behind a cheap one used daily. Zero when it has never fired and there is no average.
    /// </summary>
    public decimal AverageCost => Activations == 0 ? 0m : Spend.Cost / Activations;
}
