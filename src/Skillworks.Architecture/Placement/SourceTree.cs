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

    // A worktree or a clone inside the root is another checkout, which answers to its own rules.
    private static bool IsRepository(string folder) => Path.Exists(Path.Combine(folder, ".git"));
}
