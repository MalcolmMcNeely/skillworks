namespace Skillworks.Architecture.Placement.Slices;

internal sealed record CodeRoot(string Folder, bool IsFrontEnd)
{
    private const string FrontEndCode = "src";
    private const string FrontEndPackage = "package.json";

    public static IReadOnlyDictionary<string, CodeRoot?> AboveEach(string root, IEnumerable<string> folders) =>
        SourceTree.NearestAbove(folders, folder => At(root, folder));

    public static IEnumerable<CodeRootFolder> FoldersUnder(string root, IReadOnlyList<string> sourceFiles)
    {
        var folders = sourceFiles.Select(SourceTree.FolderOf).Distinct().ToList();
        var roots = AboveEach(root, folders);

        return folders
            .Where(folder => roots[folder] is not null)
            .SelectMany(folder => roots[folder]!.Climb(folder))
            .Distinct()
            .OrderBy(folder => folder.Folder, StringComparer.Ordinal);
    }

    public string PathOf(string folderName) => Folder.Length == 0 ? folderName : $"{Folder}/{folderName}";

    public string? TopFolderOf(string folder) =>
        SourceTree.Beneath(Folder, folder).Split('/') is [{ Length: > 0 } name, ..] ? name : null;

    private IEnumerable<CodeRootFolder> Climb(string folder)
    {
        var beneath = SourceTree.Beneath(Folder, folder);
        if (beneath.Length == 0)
            yield break;

        var names = beneath.Split('/');

        for (var level = 1; level <= names.Length; level++)
            yield return new CodeRootFolder(this, PathOf(string.Join('/', names.Take(level))), level);
    }

    private static CodeRoot? At(string root, string folder) =>
        Directory.EnumerateFiles(Path.Combine(root, folder), "*.csproj").Any()
            ? new CodeRoot(folder, IsFrontEnd: false)
            // The front end has no project file inside its code, so the package file beside it is what marks the root.
            : Path.GetFileName(folder) == FrontEndCode
            && File.Exists(Path.Combine(root, SourceTree.FolderOf(folder), FrontEndPackage))
                ? new CodeRoot(folder, IsFrontEnd: true)
                : null;
}
