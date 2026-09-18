namespace Skillworks.Architecture.Placement.Slices;

internal static class SharedStaysBelow
{
    public const string Rule = "shared-stays-below";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules)
    {
        var shared = rules.SharedFolderName(frontEnd: false);

        return SliceRead.In(root, sourceFiles, rules)
            .Where(read => read.TopFolder == shared)
            .GroupBy(read => read.CodeFile, StringComparer.Ordinal)
            .Select(reads => new Breach(
                Rule,
                reads.Key,
                $"This file sits in `{shared}` and reads {SliceRead.Naming(reads)}. " +
                $"`{shared}` never reads a Slice. Move the piece it needs down into `{shared}`, " +
                "or move this file up into the Slice whose job it serves."));
    }
}
