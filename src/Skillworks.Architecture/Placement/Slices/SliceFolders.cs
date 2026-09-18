namespace Skillworks.Architecture.Placement.Slices;

internal static class SliceFolders
{
    public const string Rule = "slice-folders";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules)
    {
        foreach (var folder in CodeRoot.FoldersUnder(root, sourceFiles))
        {
            var frontEnd = folder.Root.IsFrontEnd;
            var shared = rules.SharedFolderName(frontEnd);

            if (folder.Level == 1 && !rules.IsSliceOrShared(folder.Name, frontEnd))
            {
                yield return new Breach(
                    Rule,
                    folder.Folder,
                    $"A folder at the top of a code root is a Slice or `{shared}`. Move this code into " +
                    $"{Breach.OneOf(rules.SliceAndSharedNames(frontEnd))}, or name a new Slice in `slices` first.");
            }
            else if (folder.Level > 1 && rules.IsSharedInAnyCase(folder.Name))
            {
                yield return new Breach(
                    Rule,
                    folder.Folder,
                    $"`{shared}` sits at the top of a code root and nowhere else. Move this code into " +
                    $"`{folder.Root.PathOf(shared)}`, or into the Slice whose job it serves.");
            }
        }
    }
}
