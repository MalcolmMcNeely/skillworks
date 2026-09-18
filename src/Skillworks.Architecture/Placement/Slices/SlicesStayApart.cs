namespace Skillworks.Architecture.Placement.Slices;

internal static class SlicesStayApart
{
    public const string Rule = "slices-stay-apart";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules) =>
        SliceRead.In(root, sourceFiles, rules)
            .Where(read => rules.IsSlice(read.TopFolder, frontEnd: false) && read.Slice != read.TopFolder)
            .GroupBy(read => read.CodeFile, StringComparer.Ordinal)
            .Select(reads => new Breach(
                Rule,
                reads.Key,
                $"This file sits in `{reads.First().TopFolder}` and reads {SliceRead.Naming(reads)}. " +
                "A Slice never reads another Slice. Move the piece both jobs need down into " +
                $"`{rules.SharedFolderName(frontEnd: false)}`, or give `{reads.First().TopFolder}` one of its own."));
}
