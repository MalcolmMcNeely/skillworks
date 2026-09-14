namespace Skillworks.Core.Skills;

// Drawn from all history, not the filtered rows, so a filter that empties the table still offers a way out.
public sealed record FilterChoices(IReadOnlyList<string> Repositories, IReadOnlyList<string> Skills);
