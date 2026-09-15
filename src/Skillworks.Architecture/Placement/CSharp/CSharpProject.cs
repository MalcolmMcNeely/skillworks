using System.Xml.Linq;

namespace Skillworks.Architecture.Placement.CSharp;

internal sealed record CSharpProject(string Name, string RootNamespace, string Folder)
{
    private const string TestProjectSuffix = ".Tests";

    public static IReadOnlyDictionary<string, CSharpProject?> AboveEach(string root, IEnumerable<string> folders)
    {
        var projects = new Dictionary<string, CSharpProject?>();

        foreach (var folder in folders)
            Above(root, folder, projects);

        return projects;
    }

    public string? TestedProjectName =>
        Name.EndsWith(TestProjectSuffix, StringComparison.Ordinal) ? Name[..^TestProjectSuffix.Length] : null;

    public string NamespaceFor(string folder) =>
        RelativePathOf(folder) is { Length: > 0 } path ? $"{RootNamespace}.{path.Replace('/', '.')}" : RootNamespace;

    public string FolderMirroredIn(CSharpProject other, string folder) => other.FolderAt(RelativePathOf(folder));

    private string RelativePathOf(string folder) =>
        folder == Folder ? "" : folder[(Folder.Length == 0 ? 0 : Folder.Length + 1)..];

    private string FolderAt(string relativePath) =>
        relativePath.Length == 0 ? Folder
        : Folder.Length == 0 ? relativePath
        : $"{Folder}/{relativePath}";

    private static CSharpProject? Above(string root, string folder, Dictionary<string, CSharpProject?> projects)
    {
        if (projects.TryGetValue(folder, out var known))
            return known;

        var projectFile = Directory
            .EnumerateFiles(Path.Combine(root, folder), "*.csproj")
            .Order(StringComparer.Ordinal)
            .FirstOrDefault();

        var project = projectFile is not null
            ? Read(projectFile, folder)
            : folder.Length > 0
                ? Above(root, SourceTree.FolderOf(folder), projects)
                : null;

        projects[folder] = project;
        return project;
    }

    private static CSharpProject Read(string projectFile, string folder)
    {
        var name = Path.GetFileNameWithoutExtension(projectFile);

        // Old-style project files put every element in the MSBuild XML namespace, so the match ignores it.
        var rootNamespace = XDocument
            .Load(projectFile)
            .Descendants()
            // MSBuild keeps the last value a property is set to.
            .LastOrDefault(element => element.Name.LocalName == "RootNamespace")
            ?.Value
            .Trim();

        return new CSharpProject(name, string.IsNullOrEmpty(rootNamespace) ? name : rootNamespace, folder);
    }
}
