namespace Skillworks.Core.Skills;

/// <summary>One row of the skill table, shaped so the front end can render it without arithmetic.</summary>
/// <param name="Name">As invoked: <c>&lt;plugin&gt;:&lt;skill&gt;</c> for a skill delivered by a plugin.</param>
/// <param name="Activations">How many times it fired. Zero means it exists and never has.</param>
/// <param name="Repositories">Distinct repositories it fired in, sorted.</param>
/// <param name="Branches">Distinct git branches it fired on, sorted.</param>
public sealed record SkillSummary(
    string Name,
    int Activations,
    IReadOnlyList<string> Repositories,
    IReadOnlyList<string> Branches);
