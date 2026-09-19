namespace Skillworks.Architecture.Placement;

internal static class BannedFolderNames
{
    public const string Rule = "banned-folder-names";

    public static IEnumerable<Breach> Check(IReadOnlyList<string> sourceFiles, PlacementRules rules) =>
        sourceFiles
            .SelectMany(FoldersAbove)
            .Distinct()
            .Where(folder => rules.IsBanned(Path.GetFileName(folder)))
            .Order(StringComparer.Ordinal)
            .Select(folder => new Breach(
                Rule,
                folder,
                $"Rename `{Path.GetFileName(folder)}` for the job its code serves or for what the code does."));

    private static IEnumerable<string> FoldersAbove(string file)
    {
        for (var slash = file.IndexOf('/'); slash >= 0; slash = file.IndexOf('/', slash + 1))
            yield return file[..slash];
    }
}
