using System.Text.RegularExpressions;

namespace Skillworks.Architecture.Contexts;

internal sealed record Glossary(IReadOnlyList<Flattened> Headwords)
{
    // An entry's text is bold in places too, so only bold alone on its line is a headword.
    private static readonly Regex Headword = new(
        @"^\*\*(?<word>[^*\r\n]+)\*\*:[ \t]*\r?$",
        RegexOptions.Multiline);

    private static readonly string[] EndingsThatTakeEs = ["s", "x", "z", "ch", "sh"];

    public static Glossary Read(string path) =>
        new([.. Headword.Matches(File.ReadAllText(path)).Select(match => Flattened.Of(match.Groups["word"].Value))]);

    public bool Names(string name) => Holds(name) || PossibleSingularsOf(name).Any(Holds);

    private bool Holds(string name) => Headwords.Any(Flattened.Of(name).Is);

    // A folder holds many of a thing, and English spells that ending more than one way, so one singular is not enough.
    private static IEnumerable<string> PossibleSingularsOf(string name)
    {
        if (!name.EndsWith("s", StringComparison.OrdinalIgnoreCase))
            yield break;

        yield return name[..^1];

        // Without the length, `ies` alone would offer `y` and let a one-letter headword in.
        if (name.Length > 3 && name.EndsWith("ies", StringComparison.OrdinalIgnoreCase))
            yield return $"{name[..^3]}y";

        if (name.EndsWith("es", StringComparison.OrdinalIgnoreCase)
            && EndingsThatTakeEs.Any(ending => name[..^2].EndsWith(ending, StringComparison.OrdinalIgnoreCase)))
            yield return name[..^2];
    }
}
