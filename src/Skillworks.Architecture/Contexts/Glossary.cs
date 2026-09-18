using System.Text.RegularExpressions;

namespace Skillworks.Architecture.Contexts;

internal sealed record Glossary(IReadOnlyList<Flattened> Headwords)
{
    // An entry's text is bold in places too, so only bold alone on its line is a headword.
    private static readonly Regex Headword = new(
        @"^\*\*(?<word>[^*\r\n]+)\*\*:[ \t]*\r?$",
        RegexOptions.Multiline);

    public static Glossary Read(string path) =>
        new([.. Headword.Matches(File.ReadAllText(path)).Select(match => Flattened.Of(match.Groups["word"].Value))]);

    public bool Names(string name) => Headwords.Any(Flattened.Of(name).Is);
}
