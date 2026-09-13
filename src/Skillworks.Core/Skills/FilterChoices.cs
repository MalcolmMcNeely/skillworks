namespace Skillworks.Core.Skills;

/// <summary>
/// The values the three filters can be narrowed to, taken from the whole history rather than from
/// the narrowed answer, so a filter that has cut the table to nothing still offers the way back out.
/// </summary>
/// <param name="Repositories">Every repository a skill has fired in, sorted.</param>
/// <param name="Skills">Every skill that has fired or that the catalogue holds, sorted.</param>
public sealed record FilterChoices(IReadOnlyList<string> Repositories, IReadOnlyList<string> Skills);
