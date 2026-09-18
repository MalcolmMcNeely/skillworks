namespace Skillworks.Architecture.Placement;

internal static class SourceTree
{
    // Hidden folders are walked too, so a Windows checkout scans the same files as a Linux one.
    private static readonly EnumerationOptions EveryEntry = new() { AttributesToSkip = 0 };

    public static IReadOnlyList<string> Find(string root, PlacementRules rules)
    {
        var sourceFiles = new List<string>();
        var folders = new Stack<string>([root]);

        while (folders.TryPop(out var folder))
        {
            sourceFiles.AddRange(Directory
                .EnumerateFiles(folder, "*", EveryEntry)
                .Where(file => rules.IsSourceFile(Path.GetFileName(file)))
                .Select(file => Path.GetRelativePath(root, file).Replace('\\', '/')));

            foreach (var subfolder in Directory.EnumerateDirectories(folder, "*", EveryEntry))
            {
                if (!rules.IsSkipped(Path.GetFileName(subfolder)) && !IsRepository(subfolder))
                    folders.Push(subfolder);
            }
        }

        sourceFiles.Sort(StringComparer.Ordinal);
        return sourceFiles;
    }

    public static string FolderOf(string path) => path.LastIndexOf('/') is var slash and >= 0 ? path[..slash] : "";

    public static string Beneath(string root, string folder) =>
        folder == root ? "" : folder[(root.Length == 0 ? 0 : root.Length + 1)..];

    public static IReadOnlyDictionary<string, T?> NearestAbove<T>(IEnumerable<string> folders, Func<string, T?> at)
        where T : class
    {
        var found = new Dictionary<string, T?>();

        foreach (var folder in folders)
            Nearest(folder, at, found);

        return found;
    }

    private static T? Nearest<T>(string folder, Func<string, T?> at, Dictionary<string, T?> found)
        where T : class
    {
        if (found.TryGetValue(folder, out var known))
            return known;

        var nearest = at(folder) ?? (folder.Length > 0 ? Nearest(FolderOf(folder), at, found) : null);

        found[folder] = nearest;
        return nearest;
    }

    // A worktree or a clone inside the root is another checkout, which answers to its own rules.
    private static bool IsRepository(string folder) => Path.Exists(Path.Combine(folder, ".git"));
}
