using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture.Words;

internal sealed record WordRules(IReadOnlyList<string> BannedWords, IReadOnlyList<string> SkipFolders)
{
    public const string RelativePath = ".claude/rules/words.md";

    public static WordRules Read(RulesFile file) =>
        new(file.RequireList("banned-words"), file.RequireList("skip-folders"));

    public bool Skips(string path) =>
        path.Split('/')[..^1].Any(folder => SkipFolders.Contains(folder, StringComparer.Ordinal));
}
