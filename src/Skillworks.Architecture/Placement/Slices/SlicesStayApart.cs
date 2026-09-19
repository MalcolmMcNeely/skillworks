namespace Skillworks.Architecture.Placement.Slices;

internal static class SlicesStayApart
{
    public const string Rule = "slices-stay-apart";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules) =>
        [.. InFiles(root, sourceFiles, rules), .. InProjects(root, sourceFiles, rules)];

    private static IEnumerable<Breach> InFiles(
        string root,
        IReadOnlyList<string> sourceFiles,
        PlacementRules rules) =>
        SliceRead.In(root, sourceFiles, rules)
            .Where(read => rules.IsSlice(read.TopFolder, frontEnd: false) && read.Slice != read.TopFolder)
            .GroupBy(read => read.CodeFile, StringComparer.Ordinal)
            .Select(reads => new Breach(
                Rule,
                reads.Key,
                $"This file sits in `{reads.First().TopFolder}` and reads {SliceRead.Naming(reads)}. " +
                "A Slice never reads another Slice. Move the piece both jobs need down into " +
                $"`{rules.SharedFolderName(frontEnd: false)}`, or give `{reads.First().TopFolder}` one of its own."));

    private static IEnumerable<Breach> InProjects(
        string root,
        IReadOnlyList<string> sourceFiles,
        PlacementRules rules) =>
        SliceRead.ByProjects(root, sourceFiles, rules)
            .GroupBy(read => read.ProjectFile, StringComparer.Ordinal)
            .Select(reads => new Breach(
                Rule,
                reads.Key,
                $"This project names {Naming(reads)} in a `<Using>` item, which reaches every file it " +
                $"builds. Every Slice and `{rules.SharedFolderName(frontEnd: false)}` in it then reads " +
                $"`{reads.First().Slice}` with nothing in the file to say so. Put the using in the files " +
                "that need it."));

    private static string Naming(IEnumerable<ProjectRead> reads) =>
        string.Join(", ", reads.Select(read => $"`{read.Namespace}`").Distinct().Order(StringComparer.Ordinal));
}
