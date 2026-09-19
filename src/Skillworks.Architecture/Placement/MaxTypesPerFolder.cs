namespace Skillworks.Architecture.Placement;

internal static class MaxTypesPerFolder
{
    public const string Rule = "max-types-per-folder";

    public static IEnumerable<Breach> Check(IReadOnlyList<string> sourceFiles, PlacementRules rules) =>
        sourceFiles
            .GroupBy(SourceTree.FolderOf)
            .Select(files => (Folder: files.Key, TypeCount: files.Select(rules.SubjectOf).Distinct().Count()))
            .Where(folder => folder.TypeCount > rules.MaxTypesPerFolder)
            .Select(folder => new Breach(
                Rule,
                folder.Folder.Length == 0 ? "." : folder.Folder,
                $"The folder holds {folder.TypeCount} types. Move types into folders beneath it, each named for " +
                $"what its types have in common, until it holds at most {rules.MaxTypesPerFolder}."));
}
