using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Words;

internal sealed record WordRules(
    IReadOnlyDictionary<string, IReadOnlyList<string>> BannedWords,
    IReadOnlyList<string> SkipFolders)
{
    public const string RelativePath = "docs/agents/rules/words.md";

    public static WordRules Read(RulesFile file) =>
        new(
            file.RequireListMap(
                "banned-words",
                "a map from a context name to the words that lost, such as {studio: [Widget]}"),
            file.RequireList("skip-folders"));

    public bool Skips(string path) =>
        path.Split('/')[..^1].Any(folder => SkipFolders.Contains(folder, StringComparer.Ordinal));
}
