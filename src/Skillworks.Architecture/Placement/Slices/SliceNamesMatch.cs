namespace Skillworks.Architecture.Placement.Slices;

internal static class SliceNamesMatch
{
    public const string Rule = "slice-names-match";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules)
    {
        foreach (var folder in CodeRoot.FoldersUnder(root, sourceFiles))
        {
            // The rule that every top folder is a Slice already judges the top, so judging it here says it twice.
            if (folder.Level == 1)
                continue;

            // A Slice hidden under a folder of another name is out of reach: nothing else ties that folder to the job.
            if (rules.SliceNamedInAnyCase(folder.Name) is not { } slice)
                continue;

            var sliceFolder = rules.SliceFolderName(slice, folder.Root.IsFrontEnd);

            yield return new Breach(
                Rule,
                folder.Folder,
                $"`{slice}` is a Slice, and a Slice sits at the top of a code root under one name in that " +
                $"language's own case. Move this folder to `{folder.Root.PathOf(sliceFolder)}`, or rename it to " +
                "what its code does.");
        }
    }
}
