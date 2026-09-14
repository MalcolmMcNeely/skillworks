using Skillworks.Architecture.Placement.CSharp;

namespace Skillworks.Architecture.Placement;

internal static class NamespaceFollowsFolder
{
    public const string Rule = "namespace-follows-folder";

    public static IEnumerable<Breach> Check(string root, IReadOnlyList<string> sourceFiles)
    {
        var csharpFiles = sourceFiles.Where(CSharpFile.IsCSharp).ToList();
        var projects = CSharpProject.AboveEach(root, csharpFiles.Select(SourceTree.FolderOf));

        foreach (var file in csharpFiles)
        {
            var folder = SourceTree.FolderOf(file);

            // A file outside every project, such as a script run on its own, has no root namespace to follow.
            if (projects[folder] is not { } project)
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
}
