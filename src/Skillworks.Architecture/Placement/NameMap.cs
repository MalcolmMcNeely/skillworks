namespace Skillworks.Architecture.Placement;

internal static class NameMap
{
    public const string Rule = "name-map";

    public static IEnumerable<Breach> Check(IReadOnlyList<string> sourceFiles, PlacementRules rules)
    {
        foreach (var file in sourceFiles)
        {
            var entries = rules.NameMapEntriesMatching(rules.SubjectOf(file));
            var folderName = Path.GetFileName(SourceTree.FolderOf(file));

            if (entries.Count == 0 || entries.Any(entry => entry.Folder == folderName))
                continue;

            yield return new Breach(
                Rule,
                file,
                $"Move the file into a folder named {OneOf(entries.Select(entry => entry.Folder).Distinct())}, " +
                $"which the name map gives to a name that matches {OneOf(entries.Select(entry => entry.Pattern))}.");
        }
    }

    private static string OneOf(IEnumerable<string> names)
    {
        var quoted = names.Select(name => $"`{name}`").ToList();
        return quoted is [var only] ? only : $"{string.Join(", ", quoted.SkipLast(1))} or {quoted[^1]}";
    }
}
