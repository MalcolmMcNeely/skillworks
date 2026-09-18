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
                $"Move the file into a folder named {Breach.OneOf(entries.Select(entry => entry.Folder).Distinct())}, " +
                $"which the name map gives to a name that matches {Breach.OneOf(entries.Select(entry => entry.Pattern))}.");
        }
    }
}
