namespace Skillworks.Architecture.Placement.Slices;

internal static class ConcernFolders
{
    public const string Rule = "concern-folders";

    // In C# a folder inside a Slice is free grouping, so only the front end answers to this rule.
    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules) =>
        CodeRoot.FoldersUnder(root, sourceFiles)
            .Where(folder => folder.Root.IsFrontEnd && folder.Level == 2)
            .Where(folder => rules.IsSlice(folder.ParentName, frontEnd: true))
            .Where(folder => !rules.IsConcern(folder.Name))
            .Select(folder => new Breach(
                Rule,
                folder.Folder,
                "A folder inside a Slice is named for the role its types play. " +
                $"Move this code into {Breach.OneOf(rules.Concerns)}."));
}
