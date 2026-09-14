namespace Skillworks.Architecture.Placement;

internal static class NamespaceFollowsFolder
{
    public const string Rule = "namespace-follows-folder";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles)
    {
        var projects = new Dictionary<string, Project?>();

        foreach (var file in sourceFiles.Where(CSharpFile.IsCSharp))
        {
            var folder = FolderOf(file);

            // A file outside every project, such as a script run on its own, has no root namespace to follow.
            if (ProjectAbove(root, folder, projects) is not { } project)
                continue;

            var csharp = CSharpFile.Read(root, file);

            // The Program class that top-level statements make lives in no namespace, and a part of it must too.
            if (csharp.HasTopLevelStatements)
                continue;

            var expected = project.NamespaceFor(folder);
            if (csharp.TopLevelTypes.All(type => type.Namespace == expected))
                continue;

            yield return new Breach(
                Rule,
                file,
                $"Change the namespace to `{expected}`, which is the project name and then the folder path.");
        }
    }

    private static Project? ProjectAbove(string root, string folder, Dictionary<string, Project?> projects)
    {
        if (projects.TryGetValue(folder, out var known))
            return known;

        var projectFile = Directory
            .EnumerateFiles(Path.Combine(root, folder), "*.csproj")
            .Order(StringComparer.Ordinal)
            .FirstOrDefault();

        var project = projectFile is not null
            ? new Project(Path.GetFileNameWithoutExtension(projectFile), folder)
            : folder.Length > 0
                ? ProjectAbove(root, FolderOf(folder), projects)
                : null;

        projects[folder] = project;
        return project;
    }

    private static string FolderOf(string path) => path.LastIndexOf('/') is var slash and >= 0 ? path[..slash] : "";

    private sealed record Project(string Name, string Folder)
    {
        public string NamespaceFor(string folder) =>
            folder == Folder
                ? Name
                : $"{Name}.{folder[(Folder.Length == 0 ? 0 : Folder.Length + 1)..].Replace('/', '.')}";
    }
}
