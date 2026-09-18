using Skillworks.Architecture.Placement.CSharp;

namespace Skillworks.Architecture.Placement.Slices;

internal sealed record SliceRead(string CodeFile, string TopFolder, string Slice, string Namespace)
{
    // Every cross-namespace read in this repository's code files goes through a using directive in the file.
    public static IEnumerable<SliceRead> In(string root, IReadOnlyList<string> sourceFiles, PlacementRules rules)
    {
        var csharpFiles = sourceFiles.Where(CSharpFile.IsCSharp).ToList();
        var folders = csharpFiles.Select(SourceTree.FolderOf).Distinct().ToList();
        var roots = CodeRoot.AboveEach(root, folders);
        var projects = CSharpProject.AboveEach(root, folders);
        var slices = SliceNamespaces(folders, roots, projects, rules);

        foreach (var file in csharpFiles)
        {
            // A test may read any Slice, because one that checks a seam has to see both sides.
            if (rules.IsTestFile(Path.GetFileName(file)))
                continue;

            var folder = SourceTree.FolderOf(file);

            if (TopFolderIn(roots, folder) is not { } top || !rules.IsSliceOrShared(top.Name, frontEnd: false))
                continue;

            foreach (var read in CSharpFile.Read(root, file).Usings)
            {
                if (SliceNamed(slices, read) is { } slice)
                    yield return new SliceRead(file, top.Name, slice, read);
            }
        }
    }

    public static string Naming(IEnumerable<SliceRead> reads) =>
        string.Join(", ", reads.Select(read => $"`{read.Namespace}`").Distinct().Order(StringComparer.Ordinal));

    // Only C# reaches a Slice by namespace, so the front end answers to the boundary rules of its own linter.
    private static (CodeRoot Root, string Name)? TopFolderIn(
        IReadOnlyDictionary<string, CodeRoot?> roots,
        string folder) =>
        roots[folder] is { IsFrontEnd: false } codeRoot && codeRoot.TopFolderOf(folder) is { } name
            ? (codeRoot, name)
            : null;

    private static IReadOnlyList<(string Namespace, string Slice)> SliceNamespaces(
        IEnumerable<string> folders,
        IReadOnlyDictionary<string, CodeRoot?> roots,
        IReadOnlyDictionary<string, CSharpProject?> projects,
        PlacementRules rules)
    {
        var slices = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var folder in folders)
        {
            if (TopFolderIn(roots, folder) is not { } top
                || !rules.IsSlice(top.Name, frontEnd: false)
                || projects[folder] is not { } project)
                continue;

            slices[project.NamespaceFor(top.Root.PathOf(top.Name))] = top.Name;
        }

        // One project's root namespace can sit inside another's, so the longest namespace is the one that matched.
        return [.. slices.OrderByDescending(slice => slice.Key.Length).Select(slice => (slice.Key, slice.Value))];
    }

    private static string? SliceNamed(IReadOnlyList<(string Namespace, string Slice)> slices, string read)
    {
        foreach (var slice in slices)
        {
            if (read == slice.Namespace || read.StartsWith($"{slice.Namespace}.", StringComparison.Ordinal))
                return slice.Slice;
        }

        return null;
    }
}
